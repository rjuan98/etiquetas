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
import json

from flask import Blueprint, request, jsonify, send_file, current_app

from loja import catalogo, cobranca, rede
from dados import modelos as tabela_modelos, impressoes
from etiquetas import esquema, formatos, receitas
from etiquetas.motores import zpl as motor_zpl, pdf as motor_pdf, svg as motor_svg
from .sessao import exige_loja
from . import config

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
    # Loja de desenvolvimento devolve catálogo de mentira, pra tela ser testável
    # sem conta de Shopify. Só vale quando MODO_DEV está ligado E o token é o
    # falso — ver `dev.loja_de_mentira`. Com uma loja de verdade instalada, isto
    # não pode aparecer no lugar do catálogo dela.
    if config.MODO_DEV:
        from . import dev
        if dev.loja_de_mentira(loja):
            itens = dev.catalogo_falso(request.args.get("busca"))
            for item in itens:
                item["quantidade"] = catalogo.quantidade_sugerida(item)
            return jsonify({"itens": itens, "tem_mais": False, "cursor": None})

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


# ------------------------------------------------------------------- receita

# Dados de exemplo pra prévia, quando o lojista ainda não escolheu produto. Sem
# isto a primeira tela do app é uma etiqueta em branco, e etiqueta em branco
# parece app quebrado.
EXEMPLO = {
    "produto": {"titulo": "Caneca de Porcelana Branca 300ml",
                "fornecedor": "Cerâmica Real", "tipo": "Caneca"},
    "variante": {"titulo": "Branca / 300ml", "sku": "CAN-BR-300",
                 "preco": "39.90", "preco_comparado": "49.90",
                 "codigo_barras": "7891234567895"},
    "loja": {"nome": "Sua loja"},
}


def _receita_do_pedido(dados: dict):
    """Monta o Template a partir das escolhas que vieram da tela.

    Recebe só coisa que o lojista sabe responder — formato, quais campos, como
    mostrar o preço. A tradução pra coordenada mora em `receitas.py`, no
    servidor, pra que a etiqueta que aparece na prévia seja a que imprime.
    """
    r = dados.get("receita") or {}
    campos = r.get("campos")
    return receitas.montar(
        formato=r.get("formato") or "zebra_2x1",
        campos=tuple(campos) if isinstance(campos, list) else receitas.PADRAO,
        simbolo=str(r.get("simbolo", "R$"))[:4],
        simbolo_depois=bool(r.get("simbolo_depois")),
        separador_decimal=str(r.get("separador_decimal", ","))[:1] or ",",
        separador_milhar=str(r.get("separador_milhar", "."))[:1],
        rotulo_sku=bool(r.get("rotulo_sku", True)),
        simbologia=str(r.get("simbologia", "EAN13")),
        desvio_x_mm=float(r.get("desvio_x_mm") or 0),
        desvio_y_mm=float(r.get("desvio_y_mm") or 0),
        nome=str(r.get("nome") or ""))


def _template_do_pedido(dados: dict):
    """O template, venha ele da receita ou do modelo cru.

    A tela normal manda `receita` — as escolhas. `modelo` continua aceito pra
    quem já tem um template pronto (importado, ou de uma versão futura com
    editor livre). Os dois caminhos passam pela MESMA validação depois.
    """
    if dados.get("receita"):
        return _receita_do_pedido(dados)
    return esquema.de_dict(dados.get("modelo") or {})


@rotas.get("/formatos")
@exige_loja
def lista_de_formatos(loja):
    """O catálogo de papel e os campos disponíveis, pra tela montar os menus."""
    return jsonify({
        "formatos": [{
            "codigo": f.codigo, "nome": f.nome, "fabricante": f.fabricante,
            "largura_mm": f.midia.largura_mm, "altura_mm": f.midia.altura_mm,
            "tipo": f.midia.tipo, "conferido": f.conferido,
            "por_folha": (f.midia.colunas * f.midia.linhas
                          if f.midia.tipo == "folha" else 0),
        } for f in formatos.CATALOGO],
        "campos": [{"chave": k, "nome": v["nome"]} for k, v in receitas.CAMPOS.items()],
        "padrao": list(receitas.PADRAO),
    })


@rotas.post("/previa")
@exige_loja
def previa(loja):
    """Escolhas + um produto → o SVG da etiqueta.

    Sai do servidor, pelo mesmo caminho que gera o ZPL e o PDF. Desenhar isto no
    navegador seria mais rápido e mentiria: a quebra de linha do JavaScript
    discordaria da do Python, e a prévia mostraria uma etiqueta que a impressora
    não vai imprimir.
    """
    dados = request.get_json(silent=True) or {}
    try:
        template = _receita_do_pedido(dados)
    except (ValueError, KeyError) as erro:
        return jsonify({"erro": str(erro)}), 400

    item = dados.get("item") or EXEMPLO
    try:
        desenho = motor_svg.render(template, item)
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400

    r = dados.get("receita") or {}
    campos = r.get("campos")
    return jsonify({
        "svg": desenho,
        # O que o lojista pediu e não coube. Sem isto ele liga "fornecedor", não
        # vê diferença nenhuma e conclui que o app está quebrado.
        "nao_coube": receitas.cabem_os_campos(
            r.get("formato") or "zebra_2x1",
            tuple(campos) if isinstance(campos, list) else receitas.PADRAO),
        "largura_mm": template.midia.largura_mm,
        "altura_mm": template.midia.altura_mm,
    })


@rotas.post("/calibracao.pdf")
@exige_loja
def calibracao(loja):
    """A régua impressa. É a resposta pra reclamação nº 1: "etiqueta sai torta".

    Sem ela, "está torto" não tem conversa possível — o lojista não sabe dizer
    QUANTO, e a gente não tem o que corrigir.
    """
    dados = request.get_json(silent=True) or {}
    try:
        template = _receita_do_pedido(dados)
    except (ValueError, KeyError) as erro:
        return jsonify({"erro": str(erro)}), 400

    buffer = io.BytesIO(motor_pdf.pagina_de_calibracao(template))
    return send_file(buffer, mimetype="application/pdf", as_attachment=True,
                     download_name="calibracao.pdf")


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
    try:
        receita_salva = json.loads(registro.get("receita") or "{}")
    except ValueError:
        receita_salva = {}
    return jsonify({"id": registro["id"], "nome": registro["nome"],
                    # A receita é o que reabre o editor com os botões certos. Sem
                    # ela dava pra imprimir e não dava pra editar.
                    "receita": receita_salva,
                    "modelo": esquema.para_dict(esquema.de_json(registro["json"]))})


@rotas.post("/modelos")
@exige_loja
def criar_modelo(loja):
    dados = request.get_json(silent=True) or {}

    # Validar o que veio ANTES de conferir o plano. Responder "assine o Pro" pra
    # quem mandou um modelo quebrado esconde o erro de verdade — e o erro de
    # verdade, nesse caso, é da nossa própria tela.
    try:
        template = _template_do_pedido(dados)
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

    novo = tabela_modelos.criar(loja["id"], dados.get("nome", ""), template,
                                dados.get("receita"))
    return jsonify({"id": novo}), 201


@rotas.put("/modelos/<int:modelo_id>")
@exige_loja
def salvar_modelo(loja, modelo_id):
    dados = request.get_json(silent=True) or {}
    try:
        template = _template_do_pedido(dados)
    except Exception as erro:
        return jsonify({"erro": "Modelo inválido: %s" % erro}), 400

    problemas = esquema.validar(template)
    if problemas:
        return jsonify({"erro": "Modelo com problemas.", "problemas": problemas}), 400

    if not tabela_modelos.salvar(loja["id"], modelo_id, dados.get("nome", ""),
                                 template, dados.get("receita")):
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

    # Dá pra imprimir sem salvar. Obrigar a salvar antes de testar transforma
    # "deixa eu ver como fica" em três cliques e uma caixa de nome — e a pessoa
    # ainda fica com uma lista de modelos chamados "teste", "teste2", "teste3".
    modelo_id = dados.get("modelo_id")
    if dados.get("receita"):
        try:
            template = _receita_do_pedido(dados)
        except (ValueError, KeyError) as erro:
            return jsonify({"erro": str(erro)}), 400
        # O `modelo_id` vira só anotação no histórico — o que imprime é a receita,
        # que é o que está na tela. Mas ele vem do navegador, então precisa ser
        # conferido: sem isso o histórico desta loja guardaria o id de um modelo
        # de outra, e o suporte olharia pro registro errado.
        if modelo_id and not tabela_modelos.buscar_cru(loja["id"], modelo_id):
            modelo_id = None
    elif modelo_id:
        template = tabela_modelos.buscar(loja["id"], modelo_id)
        if not template:
            return jsonify({"erro": "Modelo não encontrado."}), 404
    else:
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
