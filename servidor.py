"""Sobe o app. `python servidor.py`

Lê o `.env` na mão em vez de usar `python-dotenv` — são doze linhas e evita uma
dependência que só serve pra isso.

Em produção quem sobe é o gunicorn, e aí este arquivo serve de ponto de entrada:

    gunicorn "servidor:app" --bind 0.0.0.0:8000

O `criar_app()` é chamado no import justamente pra isso funcionar.
"""
import os
import sys

# Tudo é resolvido em relação a ESTE arquivo, não ao diretório de onde se chamou.
# O gunicorn costuma subir de outro lugar, e o `systemd` quase sempre — com
# caminho relativo, o `.env` não é lido e o banco nasce vazio num canto qualquer
# do disco. O sintoma é "todas as lojas sumiram", e a causa é uma linha assim.
AQUI = os.path.dirname(os.path.abspath(__file__))


def carregar_env(caminho=None):
    """Põe o `.env` no ambiente. Não sobrescreve o que já existe.

    Não sobrescrever é de propósito: em hospedagem as variáveis vêm do painel, e
    um `.env` esquecido no disco não pode ganhar delas.
    """
    caminho = caminho or os.path.join(AQUI, ".env")
    if not os.path.exists(caminho):
        return
    with open(caminho, encoding="utf-8") as arquivo:
        for linha in arquivo:
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue
            nome, valor = linha.split("=", 1)
            os.environ.setdefault(nome.strip(), valor.strip().strip('"').strip("'"))


carregar_env()

# Mesma razão: banco com caminho relativo vira um arquivo diferente pra cada
# diretório de onde o servidor for iniciado.
if not os.path.isabs(os.environ.get("BANCO_CAMINHO", "")):
    os.environ["BANCO_CAMINHO"] = os.path.join(
        AQUI, os.environ.get("BANCO_CAMINHO") or "etiquetas.db")

from web import criar_app, config  # noqa: E402  (precisa do env carregado antes)

app = criar_app()


if __name__ == "__main__":
    faltando = config.conferir()
    if faltando:
        print("Configuração incompleta:")
        for problema in faltando:
            print("  - %s" % problema)
        print("\nCopie o .env.exemplo pra .env e preencha.")
        if not config.MODO_DEV:
            sys.exit(1)
        print("\nMODO_DEV ligado: subindo assim mesmo. "
              "Nada que fale com o Shopify vai funcionar.\n")

    app.run(host="127.0.0.1", port=int(os.environ.get("PORTA", 5000)),
            debug=config.MODO_DEV)
