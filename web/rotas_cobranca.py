"""A volta do lojista depois de aprovar (ou recusar) a cobrança.

O Shopify manda ele pra cá quando ele sai da tela de confirmação. Não vem token
de sessão nem HMAC — é uma navegação de topo, fora do iframe.

## Por que isto pode ser uma rota aberta

Ela **não libera nada**. Tudo o que faz é marcar que o plano guardado venceu, o
que força a próxima requisição a perguntar ao Shopify qual é o plano de verdade.

Se alguém chamar isto de fora, o efeito é o app reconferir um plano que já ia
reconferir. Não dá pra virar Pro chamando esta URL — quem responde isso é o
Shopify, e é ele que a gente pergunta.

Escrevi isso por extenso porque "rota de retorno de pagamento sem autenticação"
soa errado, e vale saber que foi decidido em vez de esquecido.

## E ela cobre a recusa também

O Shopify manda de volta por aqui tanto quem aprovou quanto quem desistiu. Como
não confiamos no clique de qualquer jeito, os dois casos têm o mesmo tratamento:
marca vencido, pergunta depois. Quem desistiu continua no plano que tinha.
"""
from flask import Blueprint, request, redirect, abort, current_app, g

from loja import dominio
from dados import lojas
from . import textos

rotas = Blueprint("cobranca", __name__)


@rotas.get("/cobranca/volta")
def volta():
    bruto = request.args.get("shop", "")
    if not dominio.valido(bruto):
        abort(400, textos.t("erro_dominio", getattr(g, "idioma", textos.PADRAO)))

    loja = dominio.normalizar(bruto)
    registro = lojas.buscar(loja)
    if registro:
        lojas.marcar_plano_vencido(registro["id"])
        current_app.logger.info("volta da cobrança: plano marcado pra reconferir")

    # De volta pro app dentro do admin. Mandar pra nossa própria URL deixaria o
    # lojista numa página solta fora do Shopify, sem menu e sem saber voltar.
    return redirect("https://admin.shopify.com/store/%s/apps"
                    % loja.replace(".myshopify.com", ""))
