"""As configurações, num lugar só, conferidas no boot.

## Falhar no boot, não na hora do uso

Se `SHOPIFY_SEGREDO` estiver faltando, isso pode aparecer de dois jeitos:

  a) o servidor sobe, e três dias depois um webhook é recusado porque a
     assinatura não confere — e ninguém entende por quê
  b) o servidor não sobe, dizendo exatamente o que falta

O (b) é sempre melhor. Configuração errada descoberta em produção, de madrugada,
por um lojista, é o pior jeito de descobrir.

`MODO_DEV=1` afrouxa isso pra dar pra rodar no computador sem credencial nenhuma
— mas então nada que fale com o Shopify funciona, e o `conferir()` diz isso.
"""
import os


def _texto(nome, padrao=""):
    return (os.environ.get(nome) or padrao).strip()


MODO_DEV = _texto("MODO_DEV") in ("1", "true", "sim")

CHAVE_API = _texto("SHOPIFY_CHAVE_API")
SEGREDO = _texto("SHOPIFY_SEGREDO")

# A URL pública do app. Precisa ser https e **sem barra no fim** — ela é
# concatenada com "/instalar/volta", e "//instalar/volta" não bate com o que
# está cadastrado no painel do Shopify. O OAuth recusa por diferença de um
# caractere, sem explicar.
URL_DO_APP = _texto("APP_URL", "http://localhost:5000").rstrip("/")

CHAVE_SEGREDO = _texto("CHAVE_SEGREDO")

# Loja de desenvolvimento: assinatura de teste, que não cobra de verdade. Cobrar
# numa loja de teste é motivo de reprovação na revisão do Shopify.
COBRANCA_DE_TESTE = _texto("COBRANCA_TESTE", "1") in ("1", "true", "sim")


def url_de_volta() -> str:
    return "%s/instalar/volta" % URL_DO_APP


def conferir() -> list:
    """Devolve TODOS os problemas de uma vez, não o primeiro.

    Mesma escolha do `esquema.validar`: quem está configurando o servidor
    prefere a lista inteira a descobrir um erro por vez, reiniciando entre cada.
    """
    faltando = []
    if not CHAVE_SEGREDO:
        faltando.append(
            "CHAVE_SEGREDO — cifra o token de acesso das lojas no banco. "
            "Gere com: python -c \"import secrets; print(secrets.token_urlsafe(32))\"")
    if not CHAVE_API:
        faltando.append("SHOPIFY_CHAVE_API — a Client ID do app, no painel de Partner")
    if not SEGREDO:
        faltando.append("SHOPIFY_SEGREDO — a Client secret; assina webhook e token de sessão")
    if not URL_DO_APP.startswith("https://") and not MODO_DEV:
        faltando.append("APP_URL — precisa ser https em produção (o Shopify exige)")
    return faltando


def exigir():
    problemas = conferir()
    if problemas:
        raise RuntimeError(
            "Configuração incompleta:\n  - " + "\n  - ".join(problemas))
