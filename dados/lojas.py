"""A tabela de lojas: quem instalou, com que token, em que plano.

Esta é a única tabela sem `loja_id` — ela **é** a loja. Todas as outras penduram
nela, e o `id` daqui é o que filtra o resto.

## Reinstalação não pode virar loja nova

Lojista desinstala e reinstala o tempo todo — troca de plano, testa outro app,
volta. Se cada instalação criasse uma linha, os modelos que a pessoa desenhou
ficariam presos na linha velha e ela abriria o app numa tela em branco, achando
que perdeu tudo.

Por isso o `dominio` é UNIQUE e `salvar()` é um upsert: reinstalar atualiza o
token e reativa a mesma linha, com os modelos todos lá.
"""
from datetime import datetime, timezone

from . import banco
from loja import dominio as dom


def agora() -> str:
    """UTC sempre, em ISO. Loja pode estar em qualquer fuso; o banco não escolhe."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def salvar(dominio_bruto: str, token: str, escopos="") -> int:
    """Grava (ou atualiza) a loja e devolve o `id`. Idempotente.

    O domínio passa pelo `normalizar` aqui também, mesmo já tendo passado no
    OAuth. Redundância de propósito: se um dia alguém chamar isto de outro lugar,
    a validação continua existindo.
    """
    limpo = dom.normalizar(dominio_bruto)
    if not token:
        raise ValueError("não dá pra salvar loja sem token de acesso")

    cifrado = banco.cifrar(token)
    with banco.conectar() as con:
        con.execute(
            """INSERT INTO lojas (dominio, token_cifrado, escopos, instalada_em)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(dominio) DO UPDATE SET
                   token_cifrado   = excluded.token_cifrado,
                   escopos         = excluded.escopos,
                   ativa           = 1,
                   desinstalada_em = NULL""",
            (limpo, cifrado, escopos, agora()))
        linha = con.execute("SELECT id FROM lojas WHERE dominio = ?",
                            (limpo,)).fetchone()
    return int(linha["id"])


def buscar(dominio_bruto: str):
    """A loja pelo domínio, ou None. O token já vem decifrado.

    Domínio inválido devolve None em vez de estourar: quem chama isto normalmente
    está tratando entrada da web, e lá o certo é 404, não 500.
    """
    try:
        limpo = dom.normalizar(dominio_bruto)
    except ValueError:
        return None

    with banco.conectar() as con:
        linha = con.execute("SELECT * FROM lojas WHERE dominio = ?",
                            (limpo,)).fetchone()
    if not linha:
        return None

    registro = dict(linha)
    registro["token"] = banco.decifrar(registro.pop("token_cifrado"))
    registro["ativa"] = bool(registro["ativa"])
    return registro


def por_id(loja_id: int):
    with banco.conectar() as con:
        linha = con.execute("SELECT * FROM lojas WHERE id = ?",
                            (int(loja_id),)).fetchone()
    if not linha:
        return None
    registro = dict(linha)
    registro["token"] = banco.decifrar(registro.pop("token_cifrado"))
    registro["ativa"] = bool(registro["ativa"])
    return registro


def marcar_plano(loja_id: int, plano: str):
    """Guarda o plano lido do Shopify.

    Isto é CACHE, não a verdade. Quem manda é a resposta do Shopify
    (`cobranca.plano_ativo`) — se o lojista cancelar, o banco daqui fica velho por
    alguns minutos, e liberar recurso pago com base nele seria entregar de graça.
    Serve pra pintar a tela sem uma ida à API a cada clique.
    """
    with banco.conectar() as con:
        con.execute("UPDATE lojas SET plano = ? WHERE id = ?",
                    (str(plano), int(loja_id)))


def desativar(dominio_bruto: str):
    """`app/uninstalled`: apaga o token, guarda os modelos.

    O token morre no instante da desinstalação — mantê-lo no banco é guardar
    segredo inútil. Já os modelos ficam: se a pessoa voltar semana que vem, o
    trabalho dela está lá.
    """
    try:
        limpo = dom.normalizar(dominio_bruto)
    except ValueError:
        return
    with banco.conectar() as con:
        con.execute("""UPDATE lojas
                       SET ativa = 0, token_cifrado = '', desinstalada_em = ?
                       WHERE dominio = ?""", (agora(), limpo))


def apagar(dominio_bruto: str):
    """`shop/redact`: apaga tudo mesmo. Sem volta.

    Os modelos e as impressões somem junto pelo ON DELETE CASCADE — desde que o
    `PRAGMA foreign_keys` esteja ligado, o que `banco.conectar()` faz em toda
    conexão. Se não estivesse, isto deixaria lixo órfão e a gente estaria
    respondendo "apaguei" pro Shopify sem ter apagado.
    """
    try:
        limpo = dom.normalizar(dominio_bruto)
    except ValueError:
        return
    with banco.conectar() as con:
        con.execute("DELETE FROM lojas WHERE dominio = ?", (limpo,))
