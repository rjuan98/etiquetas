"""O Shopify avisando que algo aconteceu.

## Duas regras que derrubam app na revisão

**Ler os bytes crus antes de qualquer coisa.** `request.get_data()` e nunca
`request.json` primeiro — o Flask guarda o corpo, mas basta alguém reserializar
o JSON pra assinatura nunca mais bater. Espaço a mais, ordem de chave diferente,
e pronto: todo webhook recusado, para sempre, sem erro visível.

**Responder 200 rápido, sempre.** O Shopify tem prazo curto e desiste se demora.
Aqui o trabalho é pequeno (apagar linhas), então dá pra fazer na hora — mas se um
dia crescer, a resposta sai primeiro e o trabalho vai pra fila.

E o 200 sai **até quando o tópico é desconhecido**. Responder erro pra um tópico
que a gente não trata faz o Shopify tentar de novo, e de novo, e acabar
desassinando o webhook por excesso de falha.
"""
from flask import Blueprint, request, jsonify, current_app

from loja import webhooks
from dados import lojas
from . import config

rotas = Blueprint("webhooks", __name__)


@rotas.post("/webhooks")
def receber():
    corpo = request.get_data()          # BYTES CRUS. Não trocar por request.json.

    try:
        aviso = webhooks.conferir(corpo, request.headers, config.segredos_aceitos())
    except webhooks.Recusado as erro:
        # 401 é o que o Shopify espera de webhook não autenticado. E o corpo não
        # explica o motivo: quem mandou não tem por que saber onde falhou.
        current_app.logger.warning("webhook recusado: %s", erro)
        return jsonify({"erro": "não autorizado"}), 401

    topico, loja = aviso["topico"], aviso["loja"]

    if webhooks.deve_apagar_a_loja(topico):
        lojas.apagar(loja)
        current_app.logger.info("shop/redact: loja apagada")
        return jsonify({"apagado": True}), 200

    if webhooks.deve_desativar(topico):
        # Desativar, não apagar: quem desinstala hoje pode reinstalar amanhã, e
        # perder os modelos desenhados seria destruir trabalho por engano.
        lojas.desativar(loja)
        return jsonify({"ok": True}), 200

    if topico in ("customers/data_request", "customers/redact"):
        return jsonify(webhooks.resposta_de_privacidade(topico)), 200

    if topico == "app_subscriptions/update":
        # Não confia no que veio no corpo pra liberar recurso pago: o corpo diz
        # que mudou, e a fonte da verdade é perguntar ao Shopify. Aqui só marca
        # que o cache está velho.
        registro = lojas.buscar(loja)
        if registro:
            lojas.marcar_plano(registro["id"], "conferir")
        return jsonify({"ok": True}), 200

    # Tópico que a gente não trata ainda: 200 mesmo assim, pelo motivo do topo.
    return jsonify({"ok": True, "ignorado": topico}), 200
