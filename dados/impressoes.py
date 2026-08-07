"""Quantas etiquetas cada loja gerou. Serve ao limite do plano e ao suporte.

## O que NÃO é guardado

Nada do conteúdo. Nem título de produto, nem SKU, nem preço, nem código de
barras. Só a conta: quantas, com que motor, quando.

Isso não é economia de espaço — é a mesma linha do resto do projeto. O app já não
pede escopo de cliente nem de pedido; guardar o catálogo do lojista aqui dentro
desfaria isso pela porta dos fundos, e transformaria a resposta dos webhooks de
privacidade numa meia verdade.
"""
from datetime import datetime, timezone

from . import banco
from .lojas import agora


def registrar(loja_id: int, quantidade: int, motor: str, modelo_id=None) -> int:
    dono = int(loja_id)
    if dono <= 0:
        raise ValueError("loja_id inválido: %r" % (loja_id,))
    try:
        quantos = max(0, int(quantidade))
    except (TypeError, ValueError):
        quantos = 0
    with banco.conectar() as con:
        cursor = con.execute(
            """INSERT INTO impressoes (loja_id, modelo_id, motor, quantidade, criado_em)
               VALUES (?, ?, ?, ?, ?)""",
            (dono, modelo_id, str(motor), quantos, agora()))
    return int(cursor.lastrowid)


def _comeco_do_mes() -> str:
    hoje = datetime.now(timezone.utc)
    return hoje.replace(day=1, hour=0, minute=0, second=0,
                        microsecond=0).isoformat(timespec="seconds")


def no_mes(loja_id: int) -> int:
    """Quantas etiquetas esta loja gerou no mês corrente (UTC).

    O corte é no mês do calendário, não em 30 dias corridos, porque é o que o
    lojista entende: "meu limite volta dia 1º". Janela deslizante confunde e vira
    ticket de suporte.

    `COALESCE` porque `SUM` de zero linhas devolve NULL, não 0 — e `int(None)`
    estoura. Loja recém-instalada cai exatamente nesse caso, ou seja, é o
    primeiro uso do app que quebraria.
    """
    dono = int(loja_id)
    with banco.conectar() as con:
        linha = con.execute(
            """SELECT COALESCE(SUM(quantidade), 0) AS n FROM impressoes
               WHERE loja_id = ? AND criado_em >= ?""",
            (dono, _comeco_do_mes())).fetchone()
    return int(linha["n"])


def historico(loja_id: int, limite=50) -> list:
    dono = int(loja_id)
    with banco.conectar() as con:
        linhas = con.execute(
            """SELECT * FROM impressoes WHERE loja_id = ?
               ORDER BY id DESC LIMIT ?""",
            (dono, max(1, min(500, int(limite))))).fetchall()
    return [dict(l) for l in linhas]
