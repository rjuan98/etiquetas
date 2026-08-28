"""Webhooks: o Shopify avisando que algo aconteceu.

Três deles são **obrigatórios pra ser aprovado na loja de apps**, e são os de
privacidade. Não é opcional e não dá pra responder qualquer coisa: o Shopify
testa na revisão.

    customers/data_request   um cliente pediu os dados que você tem dele
    customers/redact         um cliente pediu pra apagar os dados dele
    shop/redact              a loja desinstalou há 48h; apague tudo dela

E aqui este app tem uma vantagem que vale escrever: **ele não guarda dado de
cliente nenhum.** Não lê pedido, não lê comprador, não lê endereço. Então as duas
primeiras respostas são honestas e curtas — "não tenho nada dessa pessoa" — e
isso é verdade verificável no código, não promessa.

O terceiro apaga a loja de verdade.

## A regra que derruba app na revisão

Responder **200 rápido**, sempre. O Shopify tem prazo curto e desiste se o app
demora. Se o trabalho for pesado, responde 200 e faz depois — nunca segura a
resposta esperando terminar.

E **conferir o HMAC antes de qualquer coisa**. Sem isso, qualquer um manda
`shop/redact` e apaga os dados de um lojista.
"""

# Os que a gente assina. Os três primeiros são exigência do Shopify.
# Estas duas respostas vão pro Shopify, não pro lojista — ficam em inglês, que é
# a língua da plataforma, e não passam pela tabela de textos por isso.
EXPLICACAO_SEM_DADOS = (
    "This app does not collect or store customer data. It only reads products "
    "and variants, to build labels.")
EXPLICACAO_NADA_A_APAGAR = (
    "There was nothing to erase: this app stores no customer data.")

OBRIGATORIOS = ("customers/data_request", "customers/redact", "shop/redact")
NOSSOS = ("app/uninstalled", "app_subscriptions/update")
TODOS = OBRIGATORIOS + NOSSOS


class Recusado(Exception):
    """Webhook que não passou na conferência. Vira 401, sem detalhe pro chamador."""


def conferir(corpo: bytes, cabecalhos, segredo: str) -> dict:
    """Valida o webhook e devolve (topico, loja). Levanta `Recusado` se não bater.

    O `corpo` tem que ser os BYTES CRUS. Ler o JSON e serializar de novo antes de
    conferir quebra a assinatura pra sempre — espaço a mais, ordem de chave
    diferente, e nunca mais bate. É o erro clássico deste ponto.
    """
    from . import assinatura, dominio

    pegar = cabecalhos.get if hasattr(cabecalhos, "get") else dict(cabecalhos).get
    hmac_recebido = pegar("X-Shopify-Hmac-Sha256") or pegar("x-shopify-hmac-sha256")

    if not assinatura.webhook_confere(corpo, hmac_recebido or "", segredo):
        raise Recusado("assinatura do webhook não confere")

    topico = pegar("X-Shopify-Topic") or pegar("x-shopify-topic") or ""
    loja_bruta = pegar("X-Shopify-Shop-Domain") or pegar("x-shopify-shop-domain") or ""
    try:
        loja = dominio.normalizar(loja_bruta)
    except ValueError:
        raise Recusado("webhook sem domínio de loja válido")

    return {"topico": topico, "loja": loja}


def resposta_de_privacidade(topico: str) -> dict:
    """O que responder aos webhooks obrigatórios de privacidade.

    Este app não guarda dado de cliente. Não pede `read_customers`, não pede
    `read_orders`, e o `catalogo.py` só lê produto e variante. Então a resposta
    honesta às duas primeiras é que não há nada — e isso é verificável lendo os
    escopos em `oauth.py`, não é promessa de marketing.
    """
    if topico == "customers/data_request":
        return {"dados_do_cliente": None,
                "explicacao": EXPLICACAO_SEM_DADOS}
    if topico == "customers/redact":
        return {"apagado": True, "explicacao": EXPLICACAO_NADA_A_APAGAR}
    return {}


def deve_apagar_a_loja(topico: str) -> bool:
    """Só o `shop/redact` apaga tudo. `app/uninstalled` não.

    A diferença importa: desinstalar acontece o tempo todo, e muita gente
    reinstala no dia seguinte. Apagar os templates de quem desinstalou por
    engano seria perder o trabalho da pessoa sem necessidade — o Shopify manda o
    `shop/redact` 48h depois justamente pra isso.
    """
    return topico == "shop/redact"


def deve_desativar(topico: str) -> bool:
    """`app/uninstalled` desativa a loja mas guarda os templates.

    O token de acesso morre na hora da desinstalação, então a linha precisa ser
    marcada como inativa — senão o app fica tentando sincronizar com um token
    que não vale mais.
    """
    return topico == "app/uninstalled"
