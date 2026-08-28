"""A fábrica do app Flask.

Fábrica em vez de um `app` solto no módulo porque o teste precisa de um app com
banco temporário, sem tocar no de verdade. No projeto anterior o `app` global
tornava isso desconfortável, e o incômodo aparecia justamente quando eu queria
escrever mais teste — que é a pior hora pra ter atrito.

## O cabeçalho que decide se o app abre ou não

O app roda dentro de um `<iframe>` no admin do Shopify. Duas regras andam juntas:

  frame-ancestors https://{loja} https://admin.shopify.com
      Autoriza o iframe. **Sem isso o app não aparece** — o navegador recusa a
      moldura e o lojista vê um retângulo branco.

  nada de X-Frame-Options
      É o cabeçalho antigo pra mesma coisa, e ele não entende "só estes dois".
      Um `DENY` esquecido aqui bloqueia o app inteiro, e o sintoma é o mesmo
      retângulo branco — sem erro nenhum no log do servidor.

E o `frame-ancestors` é montado com o domínio **da requisição atual**, não fixo:
é ele que impede um site qualquer de embutir o app e capturar cliques.
"""
import hashlib
import os

from flask import Flask, request, g

from dados import banco
from . import config


def criar_app(banco_caminho=None) -> Flask:
    if banco_caminho:
        banco.CAMINHO = banco_caminho
        os.environ["BANCO_CAMINHO"] = banco_caminho

    app = Flask(__name__)

    # Só pro `state` do OAuth, que acontece fora do iframe (janela de cima), onde
    # cookie funciona. Nenhuma rota de dados usa sessão do Flask — essas usam
    # token de sessão do Shopify, como manda `sessao.py`.
    #
    # A chave sai de uma DERIVAÇÃO do segredo, não do segredo cru: ele também
    # gera a chave que cifra os tokens de acesso no banco, e um segredo usado em
    # dois lugares diferentes é um segredo que vaza por dois caminhos. Derivar
    # com rótulos distintos custa uma linha e mantém os dois independentes.
    app.secret_key = (
        hashlib.scrypt(config.CHAVE_SEGREDO.encode("utf-8"),
                       salt=b"etiquetas.cookie", n=2 ** 14, r=8, p=1, dklen=32)
        if config.CHAVE_SEGREDO else os.urandom(32))
    app.config.update(
        SESSION_COOKIE_SECURE=not config.MODO_DEV,
        SESSION_COOKIE_HTTPONLY=True,
        # `Lax` e não `Strict`: o cookie precisa sobreviver à volta do Shopify,
        # que é navegação vinda de outro site. Com `Strict` o cookie não é
        # enviado no retorno, o `state` some, e toda instalação falha.
        SESSION_COOKIE_SAMESITE="Lax",
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
        JSON_SORT_KEYS=False,
    )

    banco.iniciar()

    from . import (rotas_instalacao, rotas_webhooks, rotas_api, rotas_tela,
                   rotas_cobranca)
    app.register_blueprint(rotas_instalacao.rotas)
    app.register_blueprint(rotas_webhooks.rotas)
    app.register_blueprint(rotas_api.rotas)
    app.register_blueprint(rotas_cobranca.rotas)
    app.register_blueprint(rotas_tela.rotas)

    # A tela de desenvolvimento só existe com MODO_DEV. Não é `if` dentro de uma
    # rota: a rota simplesmente NÃO EXISTE em produção, que é a tranca mais
    # difícil de furar por engano.
    if config.MODO_DEV:
        from . import dev
        app.register_blueprint(dev.rotas)

    @app.before_request
    def escolher_idioma():
        """Descobre em que língua responder, uma vez por requisição.

        O Shopify põe `?locale=pt-BR` na URL quando abre o app embutido. Nas
        chamadas de API essa informação não existiria, então a própria tela
        repassa em `?idioma=`. E o `Accept-Language` fecha o caso de quem chegou
        por fora.

        Vem do cliente e serve só pra escolher palavra — não decide permissão
        nenhuma, então não precisa ser confiável.
        """
        from . import textos
        g.idioma = textos.idioma_de(
            request.args.get("locale")
            or request.args.get("idioma")
            or request.headers.get("Accept-Language"))

    @app.after_request
    def cabecalhos(resposta):
        loja = request.args.get("shop", "")
        from loja import dominio
        if dominio.valido(loja):
            moldura = "frame-ancestors https://%s https://admin.shopify.com;" % loja
        else:
            moldura = "frame-ancestors https://*.myshopify.com https://admin.shopify.com;"

        resposta.headers["Content-Security-Policy"] = moldura
        # Se algum lugar tiver posto isto, tira: bloquearia o iframe inteiro.
        resposta.headers.pop("X-Frame-Options", None)
        resposta.headers["X-Content-Type-Options"] = "nosniff"
        resposta.headers["Referrer-Policy"] = "no-referrer-when-downgrade"
        return resposta

    @app.get("/saude")
    def saude():
        """Pra hospedagem saber que o app está de pé, e pra mim saber o que falta.

        Não conta loja nem mostra dado de ninguém — só diz se a configuração está
        completa. Painel que expõe dado de cliente é linha que este projeto não
        cruza.
        """
        return {"ok": True, "configuracao_faltando": config.conferir()}

    return app
