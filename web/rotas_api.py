"""A API que a tela usa. Toda rota daqui exige token de sessão.

Nenhuma delas recebe a loja por parâmetro — ela vem do token assinado, pelo
`@exige_loja`. Ver `sessao.py` pra o porquê.

## Onde o limite do plano é conferido

**Antes de renderizar**, sempre. Duas razões, e a segunda é a que importa:

  1. gerar 4 mil etiquetas em PDF e só então dizer "seu plano não permite" gasta
     CPU do servidor à toa
  2. se a conferência viesse depois, bastaria a requisição cair no meio pra
     etiqueta sair sem ser contada
"""
import io

from flask import Blueprint, request, jsonify, send_file, current_app

from loja import catalogo, cobranca, rede
from dados import modelos as tabela_modelos, impressoes
from etiquetas import esquema
from etiquetas.motores import zpl as motor_zpl, pdf as motor_pdf
from .sessao import exige_loja

rotas = Blueprint("api", __name__, url_prefix="/api")

# Teto por requisição, independente de plano. Não é comercial, é de servidor:
# uma loja com 200 mil variantes num clique só travaria o processo pra todo mundo.
TETO_POR_VEZ = 5000


# ------------------------------------------------------------------ catálogo

@rotas.get("/produtos")
@exige_loja
def produtos(loja):
    """O catálogo, já traduzido pro formato que o motor entende.

    A busca e o cursor vão direto pro Shopify: paginar no nosso lado exigiria
    guardar o catálogo aqui, e este app não guarda catálogo de ninguém.
    """
    corpo = catalogo.consulta_de_produtos(
        quantos=request.args.get("quantos", 50),
        depois=request.args.get("depois") or None,
        busca=request.args.get("busca") or None)

    try:
        resposta = rede.graphql(loja["dominio"], loja["token"], corpo)
    except rede.ErroDeRede as erro:
        return jsonify({"erro": str(erro)}), 502

    erros = catalogo.erros_do_graphql(resposta)
    if erros:
        # GraphQL responde 200 mesmo tendo falhado. Sem isto, a tela mostraria
        # uma lista vazia e o lojista acharia que não tem produto nenhum.
        current_app.logger.warning("graphql: %s", "; ".join(erros))
        return jsonify({"erro": "O Shopify recusou a consulta.",
                        "detalhes": erros}), 502

    itens = catalogo.para_etiquetas(resposta, loja["dominio"])
    tem_mais, cursor = catalogo.tem_proxima_pagina(resposta)
    for item in itens:
        item["quantidade"] = catalogo.quantidade_sugerida(item)

    return jsonify({"itens": itens, "tem_mais": tem_mais, "cursor": cursor})


# ------------------------------------------------------------------- modelos

@rotas.get("/modelos")
@exige_loja
def listar_modelos(loja):
    return jsonify({"modelos": tabela_modelos.listar(loja["id"])})


@rotas.get("/modelos/<int:modelo_id>")
@exige_loja
def ver_modelo(loja, modelo_id):
    registro = tabela_modelos.buscar_cru(loja["id"], modelo_id)
    if not registro:
        # 404 tanto pra "não existe" quanto pra "não é seu". Distinguir os dois
        # contaria a um atacante quais id existem no banco.
        return jsonify({"erro": "Modelo não encontrado."}), 404
    return jsonify({"id": registro["id"], "nome": registro["nome"],
                    "modelo": esquema.para_dict(esquema.de_json(registro["json"]))})


@rotas.post("/modelos")
@exige_loja
def criar_modelo(loja):
    dados = request.get_json(silent=True) or {}

    # Validar o que veio ANTES de conferir o plano. Responder "assine o Pro" pra
    # quem mandou um modelo quebrado esconde o erro de verdade — e o erro de
    # verdade, nesse caso, é da nossa própria tela.
    try:
        template = esquema.de_dict(dados.get("modelo") or {})
    except Exception as erro:
        return jsonify({"erro": "Modelo inválido: %s" % erro}), 400

    problemas = esquema.validar(template)
    if problemas:
        return jsonify({"erro": "Modelo com problemas.", "problemas": problemas}), 400

    limite = cobranca.plano(_plano_de(loja))["templates"]
    if limite and tabela_modelos.quantos(loja["id"]) >= limite:
        return jsonify({"erro": "Seu plano permite %d modelo(s). "
                                "Assine o Pro pra ter modelos ilimitados." % limite,
                        "motivo": "limite_de_modelos"}), 402

    novo = tabela_modelos.criar(loja["id"], dados.get("nome", ""), template)
    return jsonify({"id": novo}), 201


@rotas.put("/modelos/<int:modelo_id>")
@exige_loja
def salvar_modelo(loja, modelo_id):
    dados = request.get_json(silent=True) or {}
    try:
        template = esquema.de_dict(dados.get("modelo") or {})
    except Exception as erro:
        return jsonify({"erro": "Modelo inválido: %s" % erro}), 400

    problemas = esquema.validar(template)
    if problemas:
        return jsonify({"erro": "Modelo com problemas.", "problemas": problemas}), 400

    if not tabela_modelos.salvar(loja["id"], modelo_id, dados.get("nome", ""), template):
        return jsonify({"erro": "Modelo não encontrado."}), 404
    return jsonify({"ok": True})


@rotas.post("/modelos/<int:modelo_id>/copia")
@exige_loja
def copiar_modelo(loja, modelo_id):
    novo = tabela_modelos.duplicar(loja["id"], modelo_id)
    if not novo:
        return jsonify({"erro": "Modelo não encontrado."}), 404
    return jsonify({"id": novo}), 201


@rotas.delete("/modelos/<int:modelo_id>")
@exige_loja
def apagar_modelo(loja, modelo_id):
    if not tabela_modelos.apagar(loja["id"], modelo_id):
        return jsonify({"erro": "Modelo não encontrado."}), 404
    return jsonify({"ok": True})


# ----------------------------------------------------------------- impressão

def _fila(itens):
    """Traduz a fila da tela pro formato dos motores, e conta junto.

    A tela manda uma lista plana — `{"produto": …, "variante": …, "quantidade": 3}`
    — porque é o que sai de `/api/produtos` e é o que JSON sabe expressar. Os
    motores querem `(dados, quantidade)` em tupla.

    Traduzir e contar na MESMA passada é de propósito. Se fossem duas funções,
    elas poderiam discordar — e aí o limite do plano contaria 50 enquanto o motor
    imprime 60. Um limite que mente é pior que nenhum limite.

    A quantidade vem do navegador, e o navegador mente: texto, negativo ou
    ausente vira 1, igualzinho ao que os motores já fazem por dentro.
    """
    fila, total = [], 0
    for item in itens:
        item = item if isinstance(item, dict) else {}
        try:
            quantos = max(1, int(float(item.get("quantidade", 1))))
        except (TypeError, ValueError):
            quantos = 1
        dados = {chave: valor for chave, valor in item.items() if chave != "quantidade"}
        fila.append((dados, quantos))
        total += quantos
    return fila, total


def _plano_de(loja) -> str:
    """O plano da loja, caindo pro grátis se for algo que a gente não conhece.

    O webhook de assinatura grava `"conferir"` pra marcar que o cache venceu. Se
    isso escorregasse pro `cobranca.plano()`, levantaria erro — ou pior, poderia
    liberar recurso pago por engano. Desconhecido é sempre o plano mais restrito.
    """
    return loja["plano"] if loja["plano"] in cobranca.PLANOS else "gratis"


@rotas.post("/imprimir")
@exige_loja
def imprimir(loja):
    dados = request.get_json(silent=True) or {}
    motor = (dados.get("motor") or "pdf").lower()
    itens = dados.get("itens") or []

    if not isinstance(itens, list) or not itens:
        return jsonify({"erro": "Nenhum item pra imprimir."}), 400

    plano = _plano_de(loja)

    if motor not in ("pdf", "zpl"):
        return jsonify({"erro": "Motor %r não existe." % motor}), 400
    if not cobranca.pode_usar(plano, motor):
        return jsonify({"erro": "Impressora térmica faz parte do plano Pro.",
                        "motivo": "motor_bloqueado"}), 402

    fila, quantas = _fila(itens)
    if quantas > TETO_POR_VEZ:
        return jsonify({"erro": "São %d etiquetas de uma vez. O limite por lote "
                                "é %d — divida em partes." % (quantas, TETO_POR_VEZ),
                        "motivo": "lote_grande"}), 400

    ja_foram = impressoes.no_mes(loja["id"])
    if not cobranca.dentro_do_limite(plano, ja_foram + quantas):
        limite = cobranca.plano(plano)["limite_etiquetas_mes"]
        return jsonify({"erro": "Você já gerou %d das %d etiquetas do mês. "
                                "Assine o Pro pra não ter limite." % (ja_foram, limite),
                        "motivo": "limite_do_mes"}), 402

    modelo_id = dados.get("modelo_id")
    template = tabela_modelos.buscar(loja["id"], modelo_id) if modelo_id else None
    if modelo_id and not template:
        return jsonify({"erro": "Modelo não encontrado."}), 404
    if not template:
        return jsonify({"erro": "Escolha um modelo de etiqueta."}), 400

    if motor == "zpl":
        saida = motor_zpl.render_lote(template, fila,
                                      dpi=int(dados.get("dpi") or 203))
        impressoes.registrar(loja["id"], quantas, motor, modelo_id)
        return current_app.response_class(saida, mimetype="text/plain; charset=utf-8")

    buffer = io.BytesIO(motor_pdf.render(template, fila))
    impressoes.registrar(loja["id"], quantas, motor, modelo_id)
    return send_file(buffer, mimetype="application/pdf",
                     as_attachment=True, download_name="etiquetas.pdf")


@rotas.get("/uso")
@exige_loja
def uso(loja):
    """Quanto já foi usado do plano. A tela precisa disso pra avisar ANTES.

    Descobrir o limite só na hora de imprimir, com a fila montada, é o tipo de
    surpresa que vira review de uma estrela.
    """
    plano = _plano_de(loja)
    detalhes = cobranca.plano(plano)
    return jsonify({
        "plano": plano,
        "nome_do_plano": detalhes["nome"],
        "etiquetas_no_mes": impressoes.no_mes(loja["id"]),
        "limite_mes": detalhes["limite_etiquetas_mes"],
        "modelos": tabela_modelos.quantos(loja["id"]),
        "limite_modelos": detalhes["templates"],
        "motores": list(detalhes["motores"]),
    })
