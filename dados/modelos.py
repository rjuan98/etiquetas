"""Os modelos de etiqueta que cada loja desenhou.

## A linha que separa uma loja da outra

Toda consulta aqui leva `loja_id` no `WHERE`, inclusive as que buscam por `id`.
Parece redundante — o `id` já é único no banco inteiro — e **não é**.

Sem isso, o lojista A abre `/modelos/57/editar`, troca o número pra 58, e vê o
modelo de outra loja. É a falha mais comum de app multi-inquilino, tem nome
(IDOR) e é sempre a mesma origem: buscar por `id` sozinho porque "o id é único".

Por isso `buscar()` não existe sem `loja_id`. Não é possível chamar errado,
porque a assinatura não permite.

## Por que JSON e não colunas

O modelo é uma árvore: mídia, calibração, lista de elementos de tipos diferentes,
cada um com campos próprios. Espalhar isso em tabelas significaria uma migração a
cada elemento novo (logo, texto girado, linha). O `esquema.py` já sabe ler e
escrever essa árvore com número de versão, então o banco guarda o texto e deixa o
`esquema.py` cuidar do formato — que é o trabalho dele.
"""
import json

from . import banco
from .lojas import agora
from etiquetas import esquema


def _loja(loja_id) -> int:
    """Recusa `loja_id` ausente ou zero antes de montar SQL.

    Se um `None` escorregasse pra dentro do WHERE, a consulta não daria erro:
    daria zero linhas em leitura e — pior — zero linhas em escrita, silenciosa.
    Melhor estourar aqui, com o nome do problema.
    """
    try:
        valor = int(loja_id)
    except (TypeError, ValueError):
        raise ValueError("loja_id inválido: %r" % (loja_id,))
    if valor <= 0:
        raise ValueError("loja_id inválido: %r" % (loja_id,))
    return valor


def listar(loja_id: int) -> list:
    """Os modelos desta loja, mais recente primeiro. Só metadado, sem o JSON.

    A lista não carrega o desenho inteiro de propósito: a tela de listagem só
    mostra nome e data, e trazer o JSON de trinta modelos pra desenhar trinta
    linhas de texto é desperdício que aparece quando a loja cresce.
    """
    dono = _loja(loja_id)
    with banco.conectar() as con:
        linhas = con.execute(
            """SELECT id, nome, criado_em, alterado_em FROM modelos
               WHERE loja_id = ? ORDER BY alterado_em DESC, id DESC""",
            (dono,)).fetchall()
    return [dict(l) for l in linhas]


def buscar(loja_id: int, modelo_id: int):
    """Um modelo, já como `Template`. None se não for desta loja.

    O `AND loja_id = ?` é a defesa contra o IDOR descrito no topo do arquivo.
    Note que "não é seu" e "não existe" devolvem a mesma coisa: None. Distinguir
    os dois casos contaria ao atacante quais `id` existem no banco.
    """
    dono = _loja(loja_id)
    with banco.conectar() as con:
        linha = con.execute(
            "SELECT * FROM modelos WHERE id = ? AND loja_id = ?",
            (int(modelo_id), dono)).fetchone()
    if not linha:
        return None
    return esquema.de_json(linha["json"])


def buscar_cru(loja_id: int, modelo_id: int):
    """O registro com o JSON em texto, sem virar `Template`.

    Serve pra quando o JSON está quebrado — modelo gravado por uma versão futura,
    ou corrompido. A tela de listagem precisa conseguir mostrar "modelo com
    problema" em vez de derrubar a página inteira.
    """
    dono = _loja(loja_id)
    with banco.conectar() as con:
        linha = con.execute(
            "SELECT * FROM modelos WHERE id = ? AND loja_id = ?",
            (int(modelo_id), dono)).fetchone()
    return dict(linha) if linha else None


def criar(loja_id: int, nome: str, template, receita=None) -> int:
    dono = _loja(loja_id)
    nome = (nome or "").strip() or "Sem nome"
    texto = esquema.para_json(template)
    momento = agora()
    with banco.conectar() as con:
        cursor = con.execute(
            """INSERT INTO modelos (loja_id, nome, json, receita, criado_em, alterado_em)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (dono, nome, texto, json.dumps(receita or {}), momento, momento))
    return int(cursor.lastrowid)


def salvar(loja_id: int, modelo_id: int, nome: str, template, receita=None) -> bool:
    """Atualiza. Devolve False se o modelo não for desta loja.

    O `AND loja_id = ?` no UPDATE é ainda mais importante que no SELECT: sem ele,
    o lojista A **sobrescreve** o modelo do lojista B. Ler o alheio é ruim;
    destruir o alheio é irreversível.
    """
    dono = _loja(loja_id)
    texto = esquema.para_json(template)
    with banco.conectar() as con:
        cursor = con.execute(
            """UPDATE modelos SET nome = ?, json = ?, receita = ?, alterado_em = ?
               WHERE id = ? AND loja_id = ?""",
            ((nome or "").strip() or "Sem nome", texto, json.dumps(receita or {}),
             agora(), int(modelo_id), dono))
    return cursor.rowcount > 0


def apagar(loja_id: int, modelo_id: int) -> bool:
    dono = _loja(loja_id)
    with banco.conectar() as con:
        cursor = con.execute("DELETE FROM modelos WHERE id = ? AND loja_id = ?",
                             (int(modelo_id), dono))
    return cursor.rowcount > 0


def quantos(loja_id: int) -> int:
    """Pro limite de modelos do plano grátis."""
    dono = _loja(loja_id)
    with banco.conectar() as con:
        linha = con.execute("SELECT COUNT(*) AS n FROM modelos WHERE loja_id = ?",
                            (dono,)).fetchone()
    return int(linha["n"])


def duplicar(loja_id: int, modelo_id: int):
    """Copiar é como a maioria das pessoas cria o segundo modelo.

    Quem desenhou uma etiqueta de 5×2,5cm e quer a de 10×5cm não quer começar do
    zero — quer a mesma coisa maior. Sem isto, a pessoa desenha tudo de novo, e
    esse é exatamente o tipo de atrito que vira review de duas estrelas.
    """
    dono = _loja(loja_id)
    original = buscar_cru(dono, modelo_id)
    if not original:
        return None
    momento = agora()
    with banco.conectar() as con:
        cursor = con.execute(
            """INSERT INTO modelos (loja_id, nome, json, receita, criado_em, alterado_em)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (dono, "%s (cópia)" % original["nome"], original["json"],
             original.get("receita") or "{}", momento, momento))
    return int(cursor.lastrowid)


def json_valido(texto: str) -> bool:
    """O JSON abre como modelo? Usado antes de gravar coisa vinda da web."""
    try:
        esquema.de_json(texto if isinstance(texto, str) else json.dumps(texto))
        return True
    except Exception:
        return False
