"""Instalação do app: a ida ao Shopify e a volta com o token.

O fluxo tem três passos e cada um tem uma armadilha:

1. **Mandar o lojista pro Shopify** com a lista de permissões que a gente quer.
   Armadilha: pedir permissão demais. Cada escopo a mais é uma tela a mais de
   susto na hora de instalar, e um motivo a mais de rejeição na revisão.

2. **O Shopify manda de volta** com um `code` de uso único.
   Armadilha: aceitar a volta sem conferir de onde veio. É aqui que entra o
   `state`, que é a defesa contra alguém forjar uma instalação.

3. **Trocar o `code` por um token permanente.**
   Armadilha: guardar o token errado, ou guardar em texto puro num lugar que
   vaza.

Este arquivo NÃO faz rede. Ele monta as URLs e o corpo da requisição, e quem
chama executa. Assim tudo aqui é testável sem credencial e sem internet.
"""
import secrets

# Só o que o app REALMENTE usa. Cada escopo a mais assusta na instalação e vira
# pergunta na revisão do Shopify — e "por que você precisa disso?" sem resposta
# boa é rejeição.
#
#   read_products    ler produto, variante, SKU, código de barras e preço
#   read_inventory   ler estoque, pra sugerir quantidade de etiqueta por produto
#
# O que a gente NÃO pede, de propósito: escrever produto, ler pedido, ler
# cliente. Um app de etiqueta não tem por que enxergar quem comprou.
ESCOPOS = ("read_products", "read_inventory")

VERSAO_API = "2026-07"


def novo_estado() -> str:
    """O `state` do OAuth: um número aleatório que amarra ida e volta.

    Sem ele, um atacante manda o lojista direto pra URL de retorno com um `code`
    obtido em outra loja, e o app instala em nome de quem não pediu. Guardar na
    sessão e conferir na volta é o que fecha isso.

    `token_urlsafe` usa a fonte de aleatoriedade do sistema — `random` comum é
    previsível e não serve pra segurança.
    """
    return secrets.token_urlsafe(32)


def url_de_autorizacao(loja: str, chave_api: str, url_de_volta: str,
                       estado: str, escopos=ESCOPOS) -> str:
    """A URL pra onde o lojista é mandado pra autorizar."""
    from urllib.parse import urlencode
    from . import dominio

    loja = dominio.normalizar(loja)
    parametros = {
        "client_id": chave_api,
        "scope": ",".join(escopos),
        "redirect_uri": url_de_volta,
        "state": estado,
    }
    return "https://%s/admin/oauth/authorize?%s" % (loja, urlencode(parametros))


def estado_confere(recebido: str, guardado: str) -> bool:
    """O `state` que voltou é o mesmo que a gente mandou?

    Comparação de tempo constante, como toda comparação de segredo neste projeto:
    o `==` normal para no primeiro byte diferente e vaza o valor pelo relógio.
    """
    import hmac
    if not recebido or not guardado:
        return False
    return hmac.compare_digest(str(recebido), str(guardado))


def troca_de_token(loja: str, chave_api: str, segredo: str, codigo: str) -> tuple:
    """(url, corpo) pra trocar o `code` pelo token permanente.

    Devolve em vez de executar pra manter este arquivo sem rede — e assim ele é
    testável hoje, sem conta de desenvolvedor.
    """
    from . import dominio
    url = "https://%s/admin/oauth/access_token" % dominio.normalizar(loja)
    return url, {"client_id": chave_api, "client_secret": segredo, "code": codigo}


def volta_valida(parametros: dict, estado_guardado: str, segredo: str) -> str:
    """Confere a volta do OAuth inteira e devolve o domínio da loja.

    Levanta ValueError com motivo em caso de recusa — e a ordem das conferências
    é de propósito: primeiro o que é barato e mais provável de estar errado.
    """
    from . import assinatura, dominio

    if not estado_confere(parametros.get("state"), estado_guardado):
        raise ValueError("o `state` não confere — instalação não foi iniciada aqui")
    if not assinatura.parametros_conferem(parametros, segredo):
        raise ValueError("os parâmetros não vieram do Shopify")
    if not parametros.get("code"):
        raise ValueError("faltou o código de autorização")
    return dominio.normalizar(parametros.get("shop"))
