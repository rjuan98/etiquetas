"""Instalação: mandar pro Shopify, receber de volta, guardar o token.

## A armadilha do iframe

O app abre dentro de um `<iframe>`. Se a instalação fizer um `redirect` normal,
o navegador tenta carregar a tela de autorização do Shopify **dentro** do iframe
— e o Shopify recusa ser embutido. O lojista vê um quadrado branco, sem erro
nenhum no log.

A saída é escapar pra janela de cima. Por isso, quando a requisição vem de dentro
do admin, a resposta não é um redirect: é uma página minúscula que muda o
`window.top.location`.

## Por que o `state` vai em cookie

O cookie do `state` é gravado na janela de cima, que é contexto de primeira
parte — ali cookie funciona normalmente. É por isso que a instalação usa sessão
do Flask enquanto o resto do app usa token de sessão do Shopify: são dois
contextos diferentes de navegador, e cada um pede uma ferramenta.
"""
from flask import (Blueprint, request, session, redirect, abort,
                   render_template_string, current_app, g)

from loja import oauth, dominio, rede
from dados import lojas
from . import config, textos

rotas = Blueprint("instalacao", __name__)


def _t(chave):
    return textos.t(chave, getattr(g, "idioma", textos.PADRAO))

# Página de escape do iframe. `window.top` porque `window.parent` só sobe um
# nível, e o admin do Shopify às vezes aninha mais de um.
ESCAPAR = """<!doctype html><meta charset="utf-8">
<title>Instalando…</title>
<script>window.top.location.href = {{ destino|tojson }};</script>
<p style="font:16px system-ui;padding:2rem">
  {{ T.abrindo_autorizacao }}
  <a href="{{ destino }}" target="_top">{{ T.clique_se_nao_abrir }}</a>
</p>"""


def _ir_para(destino: str, embutido: bool):
    if embutido:
        return render_template_string(ESCAPAR, destino=destino,
                                      T=textos.tabela(g.idioma))
    return redirect(destino)


@rotas.get("/instalar")
def instalar():
    """Começa o OAuth. É aqui que o lojista chega vindo da loja de apps."""
    loja = request.args.get("shop", "")
    if not dominio.valido(loja):
        abort(400, _t("erro_dominio"))

    estado = oauth.novo_estado()
    session["estado_oauth"] = estado
    session["loja_instalando"] = dominio.normalizar(loja)

    destino = oauth.url_de_autorizacao(loja, config.CHAVE_API,
                                       config.url_de_volta(), estado)
    return _ir_para(destino, request.args.get("embedded") == "1")


@rotas.get("/instalar/volta")
def volta():
    """O Shopify devolvendo o `code`. Confere tudo antes de trocar por token."""
    parametros = request.args.to_dict()

    try:
        loja = oauth.volta_valida(parametros, session.get("estado_oauth", ""),
                                  config.segredos_aceitos())
    except ValueError as erro:
        # O motivo exato vai pro log, não pra tela: dizer "o hmac não bateu" vs
        # "o state não bateu" ensina quem está tentando forjar onde parou.
        current_app.logger.warning("instalação recusada: %s", erro)
        abort(400, _t("erro_instalacao"))

    # O `state` é de uso único. Sem apagar, um `code` capturado poderia ser
    # reapresentado depois e ainda passar na conferência.
    session.pop("estado_oauth", None)
    session.pop("loja_instalando", None)

    url, corpo = oauth.troca_de_token(loja, config.CHAVE_API, config.SEGREDO,
                                      parametros["code"])
    try:
        resposta = rede.trocar_token(url, corpo)
    except rede.ErroDeRede as erro:
        abort(502, _t("erro_instalacao_rede") % erro)

    # Token que expira é bomba-relógio pra este app: ele funciona no dia da
    # instalação e no dia seguinte todo mundo vê erro, sem nada ter mudado. Pior,
    # o webhook precisa funcionar com ninguém logado. Não dá pra consertar aqui —
    # depende de como o app está configurado no painel — mas dá pra GRITAR, em
    # vez de guardar quieto e descobrir pelo lojista.
    # As CHAVES da resposta, nunca os valores: é o que diz o tipo do token sem
    # jogar o token no log. Na primeira instalação de verdade eu registrei só
    # `expires_in` e fiquei sem saber se `associated_user` tinha vindo junto —
    # faltou justamente a informação que decidia a questão.
    current_app.logger.info("troca de token: campos = %s",
                            sorted(k for k in resposta if k != "access_token"))
    if rede.token_expira(resposta):
        current_app.logger.error(
            "ATENCAO: o Shopify devolveu um token que EXPIRA (expires_in=%s). "
            "Este app precisa de token offline, senão para de funcionar em ~24h. "
            "Confira a configuracao do app no painel.",
            resposta.get("expires_in"))

    token = resposta["access_token"]
    lojas.salvar(loja, token, ",".join(oauth.ESCOPOS))

    # Assinar os webhooks é o passo que mais some do roteiro — e sem ele o app é
    # reprovado na revisão, porque os três de privacidade são obrigatórios.
    try:
        _assinar_webhooks(loja, token)
    except rede.ErroDeRede:
        # Não derruba a instalação por causa disso: o lojista já autorizou, e
        # falhar aqui deixaria uma loja com token e sem app. Os webhooks podem
        # ser reassinados na próxima abertura.
        pass

    return redirect("https://admin.shopify.com/store/%s/apps"
                    % loja.replace(".myshopify.com", ""))


MUTACAO_WEBHOOK = """
mutation assinar($topico: WebhookSubscriptionTopic!, $url: URL!) {
  webhookSubscriptionCreate(
    topic: $topico
    webhookSubscription: { callbackUrl: $url, format: JSON }
  ) { userErrors { message } }
}
""".strip()


def _assinar_webhooks(loja: str, token: str):
    """Assina os webhooks. Idempotente do lado do Shopify: reassinar não duplica.

    Os três de privacidade também são declarados no painel de Partner, mas
    assinar por API cobre o caso de alguém instalar antes de o painel estar
    configurado.
    """
    from loja import webhooks
    destino = "%s/webhooks" % config.URL_DO_APP
    for topico in webhooks.TODOS:
        rede.graphql(loja, token, {
            "query": MUTACAO_WEBHOOK,
            "variables": {"topico": topico.upper().replace("/", "_"),
                          "url": destino},
        })
