"""Banco: conexão, migração e a cifragem do token de acesso.

## Multi-inquilino desde a primeira linha

Toda tabela tem `loja_id` e **toda consulta filtra por ele**. Não é zelo: um
vazamento entre lojistas aqui significa uma loja vendo o catálogo e os modelos
de outra. No projeto anterior isso era mais simples (um banco por instalação);
aqui é uma linha por loja no mesmo banco, e a disciplina precisa ser explícita.

Tem teste provando que a loja B não alcança nada da loja A.

## Por que o token de acesso é cifrado

O token que o Shopify devolve dá acesso de leitura ao catálogo inteiro da loja,
e **não expira**. Se o arquivo do banco vazar — backup mal guardado, disco de
servidor descartado, cópia num pendrive — quem pegar tem acesso a todas as lojas
instaladas.

Cifrar com uma chave que mora no ambiente separa as duas coisas: o banco sozinho
não serve pra nada. Não protege de quem invade o servidor rodando (aí a chave
está na memória), mas protege do caso comum, que é backup vazando.

Sem `CHAVE_SEGREDO` no ambiente, o app **recusa a subir** em vez de guardar
token em texto puro achando que está tudo bem.
"""
import os
import sqlite3
import base64
import hashlib
from contextlib import contextmanager

from cryptography.fernet import Fernet, InvalidToken

CAMINHO = os.environ.get("BANCO_CAMINHO", "etiquetas.db")
TEMPO_LIMITE = 20


# ------------------------------------------------------------------ cifra

def _chave_fernet() -> Fernet:
    """Deriva a chave de cifragem do segredo do ambiente.

    scrypt em vez de hash simples: se o segredo for fraco (e vai ser, porque
    alguém vai pôr uma frase), scrypt torna a força bruta cara. Sal fixo porque
    a chave precisa ser a mesma entre reinícios — não é senha de usuário, é
    chave de aplicação.
    """
    segredo = os.environ.get("CHAVE_SEGREDO")
    if not segredo:
        raise RuntimeError(
            "CHAVE_SEGREDO não está no ambiente. Sem ela, o token de acesso das "
            "lojas ficaria em texto puro no banco — e um backup vazado daria "
            "acesso ao catálogo de todos os lojistas. Gere uma com "
            "`python -c \"import secrets; print(secrets.token_urlsafe(32))\"`."
        )
    bruta = hashlib.scrypt(segredo.encode("utf-8"), salt=b"etiquetas.token",
                           n=2 ** 14, r=8, p=1, dklen=32)
    return Fernet(base64.urlsafe_b64encode(bruta))


def cifrar(texto: str) -> str:
    if not texto:
        return ""
    return _chave_fernet().encrypt(texto.encode("utf-8")).decode("ascii")


def decifrar(cifrado: str) -> str:
    """Devolve "" se não abrir, em vez de estourar.

    Token que não abre significa chave trocada ou dado corrompido — e nos dois
    casos o certo é tratar como "loja precisa reinstalar", não derrubar a tela.
    """
    if not cifrado:
        return ""
    try:
        return _chave_fernet().decrypt(cifrado.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        return ""


# ---------------------------------------------------------------- conexão

@contextmanager
def conectar():
    con = sqlite3.connect(CAMINHO, timeout=TEMPO_LIMITE)
    con.row_factory = sqlite3.Row
    # Chave estrangeira não vem ligada por padrão no SQLite. Sem isso, o CASCADE
    # das tabelas filhas não roda e apagar uma loja deixa lixo órfão.
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


ESQUEMA = """
CREATE TABLE IF NOT EXISTS lojas (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    dominio           TEXT NOT NULL UNIQUE,
    token_cifrado     TEXT NOT NULL,
    escopos           TEXT NOT NULL DEFAULT '',
    plano             TEXT NOT NULL DEFAULT 'gratis',
    ativa             INTEGER NOT NULL DEFAULT 1,
    instalada_em      TEXT NOT NULL,
    desinstalada_em   TEXT
);

-- `json` é o template montado, que é o que imprime.
-- `receita` são as escolhas que o geraram (quais campos, formato, moeda). Sem
-- ela dava pra imprimir mas não dava pra EDITAR: o lojista reabriria o modelo e
-- veria os botões todos no padrão, sem relação com a etiqueta na tela.
CREATE TABLE IF NOT EXISTS modelos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    loja_id     INTEGER NOT NULL REFERENCES lojas(id) ON DELETE CASCADE,
    nome        TEXT NOT NULL,
    json        TEXT NOT NULL,
    receita     TEXT NOT NULL DEFAULT '{}',
    criado_em   TEXT NOT NULL,
    alterado_em TEXT NOT NULL
);

-- Serve pra duas coisas: o limite mensal do plano grátis, e o suporte
-- ("o que você imprimiu às 14h?"). Não guarda o conteúdo da etiqueta, só a conta.
CREATE TABLE IF NOT EXISTS impressoes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    loja_id    INTEGER NOT NULL REFERENCES lojas(id) ON DELETE CASCADE,
    modelo_id  INTEGER,
    motor      TEXT NOT NULL,
    quantidade INTEGER NOT NULL,
    criado_em  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_modelos_loja ON modelos(loja_id);
CREATE INDEX IF NOT EXISTS idx_impressoes_loja_data ON impressoes(loja_id, criado_em);
"""


# Colunas acrescentadas depois que o banco já existia em algum lugar.
# `CREATE TABLE IF NOT EXISTS` não altera tabela que já está lá: sem isto, um
# banco antigo continuaria sem a coluna nova e toda escrita quebraria — só na
# máquina de quem já tinha rodado antes, que é o pior tipo de bug pra descobrir.
ACRESCENTAR = [
    ("modelos", "receita", "TEXT NOT NULL DEFAULT '{}'"),
]


def iniciar():
    """Cria o esquema e aplica as colunas novas. Idempotente: roda a cada boot."""
    with conectar() as con:
        con.executescript(ESQUEMA)
        for tabela, coluna, tipo in ACRESCENTAR:
            existentes = {c["name"] for c in
                          con.execute("PRAGMA table_info(%s)" % tabela).fetchall()}
            if coluna not in existentes:
                con.execute("ALTER TABLE %s ADD COLUMN %s %s" % (tabela, coluna, tipo))
