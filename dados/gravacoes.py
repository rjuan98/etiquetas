"""O que o app escreveu no catálogo do lojista — e como desfazer.

## Isto é uma EXCEÇÃO à regra do projeto, e é assumida como tal

O `impressoes.py` diz que nada do conteúdo é guardado: nem título, nem SKU, nem
preço. Esta tabela guarda SKU. Não há como contornar: **desfazer exige saber o
que estava lá antes.**

Então a exceção é construída como exceção, e não deixada acontecer:

**O mínimo.** Só o id da variante, qual campo, o valor velho e o valor novo. Nem
título de produto, nem preço, nem nada que não seja necessário pra reverter.

**Só o que NÓS escrevemos.** Nunca uma cópia do catálogo. Se o app gravou 12
SKUs, são 12 linhas — não 8 mil.

**Com prazo.** Passados `DIAS_DE_GUARDA`, a linha é apagada. Desfazer é uma
rede de segurança pra quando a pessoa percebe o erro, e ninguém percebe depois
de um mês. Guardar pra sempre seria manter o catálogo do lojista aqui dentro
pela porta dos fundos.

**Declarada.** A política de privacidade fala disto. O teste de esquema do banco
falha de propósito quando uma coluna nova aparece, e é ele que obriga a reler a
política — foi assim que esta frase entrou lá.

## Por que desfazer não é opcional

Um defeito nosso aqui mexe no catálogo de quem paga, não num papel. Etiqueta
errada custa uma folha; SKU errado em 300 produtos custa o inventário da loja. A
regra 4 de `docs/gerador-de-codigo.md`: **sem desfazer, isto não sobe.**
"""
import uuid

from . import banco
from .lojas import agora

# Quanto tempo a linha de desfazer sobrevive. Trinta dias é mais que o tempo em
# que alguém percebe que gravou errado, e pouco o bastante pra isto não virar
# uma cópia permanente do catálogo alheio.
DIAS_DE_GUARDA = 30

# Os campos que o app pode escrever. Lista fechada de propósito: se um dia
# alguém tentar gravar `price` por engano, o erro aparece aqui e não na loja.
CAMPOS_GRAVAVEIS = ("sku", "codigo_barras")


def _loja(loja_id) -> int:
    """Toda consulta leva loja_id. Ver a regra de isolamento no README."""
    dono = int(loja_id)
    if dono <= 0:
        raise ValueError("loja_id inválido: %r" % (loja_id,))
    return dono


def registrar(loja_id: int, campo: str, mudancas) -> str:
    """Anota um lote de escritas e devolve o identificador dele.

    `mudancas` é uma lista de (variante_id, valor_antigo, valor_novo).

    Chamado DEPOIS de a escrita dar certo no Shopify — registrar antes criaria
    uma linha de desfazer para algo que nunca aconteceu, e aí "desfazer"
    sobrescreveria um valor que o lojista pôs à mão.
    """
    dono = _loja(loja_id)
    if campo not in CAMPOS_GRAVAVEIS:
        raise ValueError("campo %r não é gravável. Permitidos: %s"
                         % (campo, ", ".join(CAMPOS_GRAVAVEIS)))
    linhas = [(str(v), str(antigo or ""), str(novo or ""))
              for v, antigo, novo in (mudancas or []) if str(v or "").strip()]
    if not linhas:
        raise ValueError("não há mudança nenhuma para registrar")

    lote = uuid.uuid4().hex
    quando = agora()
    with banco.conectar() as con:
        con.executemany(
            """INSERT INTO gravacoes
                   (loja_id, lote, variante_id, campo,
                    valor_antigo, valor_novo, criado_em)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [(dono, lote, v, campo, antigo, novo, quando)
             for v, antigo, novo in linhas])
    return lote


def ultimo_lote(loja_id: int, campo: str = ""):
    """O lote mais recente que ainda dá pra desfazer, ou None.

    Um só, e o último: oferecer uma lista de "desfazer o de terça" é convite pra
    o lojista reverter por cima de uma edição que ele mesmo fez depois.

    `campo` restringe ao gerador que está perguntando, e isso não é enfeite:
    com dois geradores na tela, o botão "desfazer" do SKU reverteria o lote de
    código de barras se tivesse sido ele o último. O lojista clica em desfazer
    numa janela e some o trabalho que ele fez na outra.

    ## O desempate por `id`, e por que ele é obrigatório

    MEDIDO em 20/10/2026: `agora()` tem resolução de **segundo**, e duas
    chamadas a 50ms de distância devolvem a mesma string. Ordenar só por
    `criado_em` deixa duas gravações do mesmo segundo **empatadas**, e aí o
    SQLite devolve qualquer uma das duas — "o último lote" fica indefinido.

    Dois cliques seguidos caem no mesmo segundo com facilidade. O desfazer
    reverteria o lote errado, e o lojista não teria como saber.

    O `id` é AUTOINCREMENT, então ele é monotônico mesmo quando o relógio não
    tem resolução pra separar.
    """
    dono = _loja(loja_id)
    condicao, valores = "", [dono]
    if campo:
        if campo not in CAMPOS_GRAVAVEIS:
            raise ValueError("campo %r não é gravável" % campo)
        condicao = " AND campo = ?"
        valores.append(campo)
    with banco.conectar() as con:
        linha = con.execute(
            """SELECT lote, campo, COUNT(*) AS quantos,
                      MAX(criado_em) AS quando, MAX(id) AS ultimo
                 FROM gravacoes
                WHERE loja_id = ? AND desfeito_em IS NULL""" + condicao +
            """ GROUP BY lote, campo
             ORDER BY quando DESC, ultimo DESC
                LIMIT 1""", tuple(valores)).fetchone()
    return dict(linha) if linha else None


def linhas_do_lote(loja_id: int, lote: str) -> list:
    """O que foi escrito naquele lote. Filtra por loja mesmo o lote sendo único.

    Parece redundante — o `lote` é um uuid e não colide. Não é: sem o filtro,
    um lojista que descubra o identificador do lote de outro desfaria a escrita
    alheia. É a mesma razão de `modelos.buscar` levar `loja_id`.
    """
    dono = _loja(loja_id)
    with banco.conectar() as con:
        linhas = con.execute(
            """SELECT variante_id, campo, valor_antigo, valor_novo
                 FROM gravacoes
                WHERE loja_id = ? AND lote = ? AND desfeito_em IS NULL
             ORDER BY id""", (dono, str(lote))).fetchall()
    return [dict(l) for l in linhas]


def marcar_desfeito(loja_id: int, lote: str) -> int:
    """Marca o lote como revertido. Devolve quantas linhas foram marcadas.

    Marca em vez de apagar: se o desfazer falhar no meio, a linha que já voltou
    não pode ser desfeita de novo, e a que não voltou ainda precisa existir.
    """
    dono = _loja(loja_id)
    with banco.conectar() as con:
        cursor = con.execute(
            """UPDATE gravacoes SET desfeito_em = ?
                WHERE loja_id = ? AND lote = ? AND desfeito_em IS NULL""",
            (agora(), dono, str(lote)))
    return cursor.rowcount


def apagar_vencidas(dias: int = DIAS_DE_GUARDA) -> int:
    """Apaga o que passou do prazo de guarda. Devolve quantas saíram.

    É o que impede esta tabela de virar, com o tempo, uma cópia do catálogo de
    todo mundo que já usou o app.
    """
    with banco.conectar() as con:
        cursor = con.execute(
            """DELETE FROM gravacoes
                WHERE criado_em < datetime('now', ?)""",
            ("-%d days" % max(1, int(dias)),))
    return cursor.rowcount
