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

from flask import Blueprint, request, jsonify, send_file, current_app, g

from loja import catalogo, cobranca, escrita, rede
from dados import modelos as tabela_modelos, impressoes, gravacoes
from dados import lojas as tabela_lojas
from etiquetas.modelo import CodigoBarras
from etiquetas import (campos as campos_do_motor, codigos, esquema, skus,
                       formatos, receitas, unidades)
from etiquetas.motores import zpl as motor_zpl, pdf as motor_pdf, svg as motor_svg
from .sessao import exige_loja
from . import config, textos

rotas = Blueprint("api", __name__, url_prefix="/api")


def _t(chave):
    """Atalho pro texto no idioma da requisição. Ver `textos.py`."""
    return textos.t(chave, getattr(g, "idioma", textos.PADRAO))

# Teto por requisição, independente de plano. Não é comercial, é de servidor:
# uma loja com 200 mil variantes num clique só travaria o processo pra todo mundo.
TETO_POR_VEZ = 5000


# ------------------------------------------------------------------ catálogo

# Quantas páginas de catálogo a busca filtrada varre antes de devolver o que
# achou. Oito páginas de 50 são 400 produtos — o suficiente pra loja pequena
# inteira, e pouco o bastante pra não estourar o tempo da requisição numa grande.
PAGINAS_POR_FILTRO = 8


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
            itens, tem_mais, cursor = dev.catalogo_falso(
                request.args.get("busca"), request.args.get("depois"))
            vistos = len(itens)
            itens = catalogo.filtrar(itens, request.args.get("filtro") or "")
            for item in itens:
                item["quantidade"] = catalogo.quantidade_sugerida(item)
            return jsonify({
                "itens": itens, "tem_mais": tem_mais, "cursor": cursor,
                "variantes_cortadas": catalogo.produtos_com_variantes_cortadas(itens),
                "filtro": request.args.get("filtro") or "",
                "varridos": vistos if request.args.get("filtro") else None,
                "parou_no_teto": False,
            })

    filtro = request.args.get("filtro") or ""
    erro, itens, tem_mais, cursor, vistos, paginas = _varrer(
        loja, filtro, request.args.get("busca") or None,
        request.args.get("quantos", 50), request.args.get("depois") or None)
    if erro:
        return erro

    for item in itens:
        item["quantidade"] = catalogo.quantidade_sugerida(item)

    return jsonify({
        "itens": itens, "tem_mais": tem_mais, "cursor": cursor,
        "variantes_cortadas": catalogo.produtos_com_variantes_cortadas(itens),
        # Com filtro, a tela precisa saber ATÉ ONDE a gente olhou. Dizer "3
        # produtos sem código" sem dizer "entre os 400 que varri" seria deixar o
        # lojista achar que são 3 na loja inteira.
        "filtro": filtro,
        "varridos": vistos if filtro else None,
        "parou_no_teto": bool(filtro and paginas >= PAGINAS_POR_FILTRO and tem_mais),
    })


def _varrer(loja, filtro, busca, quantos, depois):
    """Busca o catálogo aplicando o filtro, atravessando páginas quando precisa.

    Devolve `(resposta_de_erro, itens, tem_mais, cursor, vistos, paginas)`. O
    erro vem como primeiro elemento em vez de exceção porque as três rotas que
    usam isto precisam devolver o mesmo 502 com o mesmo texto.

    Está fatorado porque a prévia e o aplicar do gerador precisam EXATAMENTE da
    mesma varredura — se cada um fizesse a sua, o lojista confirmaria uma tabela
    e o app gravaria outra.
    """
    # Com filtro ligado, UMA página não serve. O Shopify devolve 50 produtos e
    # talvez 2 deles estejam sem código — o lojista veria 2 e concluiria que são
    # todos. Então a gente continua buscando até juntar uma página de verdade ou
    # acabar o catálogo.
    #
    # O teto existe porque o caso oposto também é real: loja onde quase tudo tem
    # código faria isso varrer 8 mil produtos e estourar o tempo da requisição.
    # Quando o teto é alcançado, a resposta DIZ até onde olhou.
    alvo = int(quantos or 50)
    cursor = depois
    itens, tem_mais, vistos, paginas = [], False, 0, 0

    while True:
        corpo = catalogo.consulta_de_produtos(
            quantos=alvo, depois=cursor, busca=busca)
        try:
            resposta = rede.graphql(loja["dominio"], loja["token"], corpo)
        except rede.ErroDeRede as erro:
            return (jsonify({"erro": str(erro)}), 502), None, None, None, 0, 0

        erros = catalogo.erros_do_graphql(resposta)
        if erros:
            # GraphQL responde 200 mesmo tendo falhado. Sem isto, a tela
            # mostraria uma lista vazia e o lojista acharia que não tem produto.
            current_app.logger.warning("graphql: %s", "; ".join(erros))
            return ((jsonify({"erro": _t("erro_graphql"), "detalhes": erros}), 502),
                    None, None, None, 0, 0)

        pagina = catalogo.para_etiquetas(resposta, loja["dominio"])
        vistos += len(pagina)
        paginas += 1
        itens.extend(catalogo.filtrar(pagina, filtro))
        tem_mais, cursor = catalogo.tem_proxima_pagina(resposta)

        if not filtro or not tem_mais or len(itens) >= alvo:
            break
        if paginas >= PAGINAS_POR_FILTRO:
            break

    return None, itens, tem_mais, cursor, vistos, paginas


# ------------------------------------------------------------- gerador de SKU
#
# Três rotas e uma regra que decide o desenho das três:
#
#   **O SERVIDOR CALCULA O QUE GRAVA. O NAVEGADOR SÓ CONFIRMA QUAIS.**
#
# O `aplicar` não recebe os SKUs prontos da tela — ele refaz a mesma varredura e
# o mesmo cálculo da prévia, e grava só nas variantes cuja id o lojista
# confirmou. Se recebesse o valor pronto, qualquer coisa que o navegador
# mandasse iria parar no catálogo de quem paga.
#
# E se o catálogo mudou entre ver e confirmar, a conta simplesmente dá menos
# linhas — e a resposta diz quantas.


def _escolhas_do_gerador(dados):
    """Molde e filtro do pedido, com o padrão de sempre.

    O filtro só cai no padrão quando a chave **não vem**. Com `or` simples, o
    lojista que escolhesse "todos os produtos" (string vazia) teria a escolha
    trocada em silêncio por "sem SKU" — e não entenderia por que metade da loja
    sumiu da tabela.
    """
    filtro = dados.get("filtro")
    return ((dados.get("molde") or skus.MOLDE_PADRAO).strip(),
            "sem_sku" if filtro is None else str(filtro))


def _calcular_skus(loja, molde, filtro):
    """A varredura + o cálculo. É o MESMO caminho na prévia e no aplicar.

    Devolve `(erro, linhas, vistos)`. Cada linha traz o item, o SKU proposto e o
    motivo de ter sido pulado.
    """
    erro, itens, _tem_mais, _cursor, vistos, _pag = _varrer(
        loja, filtro, None, 50, None)
    if erro:
        return erro, None, 0
    # Os SKUs que a loja já usa entram na conferência de colisão — senão o
    # gerador criaria um que já pertence a outro produto.
    ja_usados = [i["variante"].get("sku") for i in itens]
    return None, skus.gerar_lote(itens, molde, ja_usados), vistos


@rotas.post("/skus/previa")
@exige_loja
def skus_previa(loja):
    """A tabela do que SERIA gravado. Não escreve nada, não pede escopo nenhum.

    É a mesma ideia da prévia da etiqueta: mostrar antes de fazer.
    """
    dados = request.get_json(silent=True) or {}
    molde, filtro = _escolhas_do_gerador(dados)

    problemas = skus.conferir_molde(molde)
    if problemas:
        return jsonify({"erro": "; ".join(problemas)}), 400

    erro, linhas, vistos = _calcular_skus(loja, molde, filtro)
    if erro:
        return erro

    return jsonify({
        "molde": molde, "filtro": filtro, "varridos": vistos,
        "linhas": [{
            "produto_id": l["item"]["produto"].get("id"),
            "variante_id": l["item"]["variante"].get("id"),
            "produto": l["item"]["produto"].get("titulo"),
            "variante": l["item"]["variante"].get("titulo"),
            "sku_atual": l["item"]["variante"].get("sku"),
            "sku": l["sku"], "pulado": l["pulado"], "aviso": l.get("aviso", ""),
        } for l in linhas],
    })


@rotas.post("/skus/aplicar")
@exige_loja
def skus_aplicar(loja):
    """Grava os SKUs confirmados, e anota o que gravou pra dar pra desfazer."""
    dados = request.get_json(silent=True) or {}
    molde, filtro = _escolhas_do_gerador(dados)
    confirmadas = {str(v) for v in (dados.get("variantes") or []) if str(v).strip()}
    if not confirmadas:
        return jsonify({"erro": _t("gerador_nada_escolhido")}), 400

    problemas = skus.conferir_molde(molde)
    if problemas:
        return jsonify({"erro": "; ".join(problemas)}), 400

    erro, linhas, _vistos = _calcular_skus(loja, molde, filtro)
    if erro:
        return erro

    # Só o que o lojista confirmou, e só o que AINDA está vazio. A segunda
    # condição é a regra que não se discute: SKU em uso está em planilha, em
    # etiqueta impressa e na cabeça de quem trabalha na loja.
    a_gravar = [(l["item"]["produto"].get("id"),
                 l["item"]["variante"].get("id"), l["sku"])
                for l in linhas
                if l["sku"] and not l["pulado"]
                and str(l["item"]["variante"].get("id")) in confirmadas]

    if not a_gravar:
        # Pode acontecer sem ninguém ter errado: o catálogo mudou entre ver e
        # confirmar. Dizer isso é melhor que responder "gravei 0" em silêncio.
        return jsonify({"erro": _t("gerador_nada_a_gravar")}), 409

    anteriores = {str(l["item"]["variante"].get("id")):
                  str(l["item"]["variante"].get("sku") or "") for l in linhas}

    gravados, falhas = [], []
    for produto_id, pares in escrita.agrupar_por_produto(a_gravar).items():
        try:
            resposta = rede.graphql(loja["dominio"], loja["token"],
                                    escrita.consulta_de_skus(produto_id, pares))
        except rede.ErroDeRede as e:
            falhas.append(str(e))
            continue
        motivos = escrita.erros_da_escrita(resposta)
        if motivos:
            falhas.extend(motivos)
            continue
        # Só o que o Shopify CONFIRMOU vira registro de desfazer. Mandar não é
        # gravar, e anotar o que não aconteceu faria o desfazer sobrescrever um
        # valor alheio.
        for variante_id, sku in escrita.variantes_gravadas(resposta).items():
            gravados.append((variante_id, anteriores.get(variante_id, ""), sku))

    lote = gravacoes.registrar(loja["id"], "sku", gravados) if gravados else ""
    return jsonify({"gravados": len(gravados), "lote": lote,
                    "falhas": falhas[:10]})


@rotas.post("/skus/desfazer")
@exige_loja
def skus_desfazer(loja):
    """Devolve cada variante do último lote ao valor que tinha antes."""
    lote = gravacoes.ultimo_lote(loja["id"])
    if not lote:
        return jsonify({"erro": _t("gerador_nada_a_desfazer")}), 404

    linhas = gravacoes.linhas_do_lote(loja["id"], lote["lote"])
    # Pra desfazer é preciso saber de que produto é cada variante, e isso não
    # está no registro — ele guarda o mínimo de propósito. Vem do catálogo.
    erro, itens, _tm, _c, _v, _p = _varrer(loja, "", None, 50, None)
    if erro:
        return erro
    produto_de = {str(i["variante"].get("id")): i["produto"].get("id")
                  for i in itens}

    voltar = [(produto_de.get(l["variante_id"]), l["variante_id"],
               l["valor_antigo"]) for l in linhas
              if produto_de.get(l["variante_id"])]
    if not voltar:
        return jsonify({"erro": _t("gerador_nada_a_desfazer")}), 404

    desfeitos, falhas = 0, []
    for produto_id, pares in escrita.agrupar_por_produto(voltar).items():
        try:
            resposta = rede.graphql(loja["dominio"], loja["token"],
                                    escrita.consulta_de_skus(produto_id, pares))
        except rede.ErroDeRede as e:
            falhas.append(str(e))
            continue
        motivos = escrita.erros_da_escrita(resposta)
        if motivos:
            falhas.extend(motivos)
            continue
        desfeitos += len(escrita.variantes_gravadas(resposta))

    if desfeitos:
        gravacoes.marcar_desfeito(loja["id"], lote["lote"])
    return jsonify({"desfeitos": desfeitos, "falhas": falhas[:10]})


# ------------------------------------------------------------------- receita

# Dados de exemplo pra prévia, quando o lojista ainda não escolheu produto. Sem
# isto a primeira tela do app é uma etiqueta em branco, e etiqueta em branco
# parece app quebrado.
def _exemplo() -> dict:
    """O produto de exemplo, no idioma de quem está olhando.

    A primeira versão era um dicionário fixo em português. Numa tela em inglês, a
    prévia — que é o elemento mais visível do app — aparecia com "Caneca de
    Porcelana Branca" e "R$ 39,90". Só apareceu tirando a captura de tela.
    """
    return {
        "produto": {"titulo": _t("exemplo_titulo"),
                    "fornecedor": _t("exemplo_fornecedor"), "tipo": ""},
        "variante": {"titulo": _t("exemplo_variante"), "sku": "MUG-WH-300",
                     "preco": "39.90", "preco_comparado": "49.90",
                     "codigo_barras": "7891234567895"},
        "loja": {"nome": ""},
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
        digitos_do_codigo=bool(r.get("digitos_do_codigo", True)),
        largura_mm=r.get("largura_mm") or 0,
        altura_mm=r.get("altura_mm") or 0,
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


# O catálogo de papel guarda o nome em português, porque quem mantém escreve em
# português. Os sufixos descritivos são traduzidos aqui, na borda — o
# `formatos.py` é do motor e não pode saber que idioma existe.
SUFIXOS_DE_FORMATO = {
    "varejo": "formato_varejo", "envio": "formato_envio",
    "multiuso": "formato_multiuso", "endereço": "formato_endereco",
    "joia, 2 abas": "formato_joia", "pol": "formato_polegada",
}


def _nome_do_formato(f) -> str:
    nome = f.nome
    for pedaco, chave in SUFIXOS_DE_FORMATO.items():
        if pedaco in nome:
            nome = nome.replace(pedaco, _t(chave))
    # "30 por folha" vira "30 per sheet"
    if " por folha" in nome:
        pos = nome.split(" por folha")[0].split()[-1]
        nome = nome.replace("%s por folha" % pos, _t("formato_por_folha") % pos)
    return nome


@rotas.get("/formatos")
@exige_loja
def lista_de_formatos(loja):
    """O catálogo de papel e os campos disponíveis, pra tela montar os menus."""
    return jsonify({
        "formatos": [{
            "codigo": f.codigo, "nome": _nome_do_formato(f), "fabricante": f.fabricante,
            "largura_mm": f.midia.largura_mm, "altura_mm": f.midia.altura_mm,
            "tipo": f.midia.tipo, "conferido": f.conferido,
            "por_folha": (f.midia.colunas * f.midia.linhas
                          if f.midia.tipo == "folha" else 0),
        } for f in formatos.CATALOGO],
        # Medida livre não é um formato do catálogo — é o lojista digitando.
        # A tela precisa do código e dos limites pra montar o campo e avisar
        # antes de mandar um número que o motor vai recusar.
        "livre": {"codigo": formatos.LIVRE,
                  "nome": _t("formato_livre"),
                  "menor_mm": formatos.MENOR_MEDIDA_MM,
                  "maior_mm": formatos.MAIOR_MEDIDA_MM},
        "campos": [{"chave": k, "nome": _t("campo_" + k)} for k in receitas.CAMPOS],
        "padrao": list(receitas.PADRAO),
    })


def _por_que_o_codigo_sumiu(template, item) -> str:
    """O motivo de o código de barras não ter sido desenhado, ou "" se foi.

    Repete a mesma pergunta que os motores fazem, na mesma ordem — e de
    propósito chama as MESMAS funções, pra não existir uma segunda opinião sobre
    o que é código válido.
    """
    for el in template.elementos:
        if not isinstance(el, CodigoBarras):
            continue
        valor = (campos_do_motor.resolver(el.campo, item) or "").strip()
        if not valor:
            return ""          # produto sem código não é erro de configuração
        simbologia = codigos.obter(el.simbologia)
        ok, motivo = codigos.validar(valor, simbologia)
        if not ok:
            return motivo
        if not codigos.cabe_na_largura(simbologia, valor, el.modulo_dots,
                                       unidades.ZEBRA_203, el.x_mm,
                                       template.midia.largura_mm, el.altura_mm):
            return _t("codigo_nao_cabe")
    return ""


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

    item = dados.get("item") or _exemplo()
    try:
        desenho = motor_svg.render(template, item)
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400

    r = dados.get("receita") or {}
    campos = r.get("campos")
    return jsonify({
        "svg": desenho,
        # Por que o código sumiu da prévia. Os motores recusam desenhar código
        # que não bipa — dígito verificador errado, tamanho errado pra
        # simbologia escolhida, ou largo demais pro papel. Isso está certo, mas
        # sumir CALADO não: o lojista escolhe ITF-14, o código some, e ele
        # conclui que o app quebrou. A frase vem do `codigos.validar`, que já é
        # escrita pra ele ler.
        "codigo_invalido": _por_que_o_codigo_sumiu(template, item),
        # O que o lojista pediu e não coube. Sem isto ele liga "fornecedor", não
        # vê diferença nenhuma e conclui que o app está quebrado.
        # Sai do template que ACABOU de ser desenhado, não de um remontado
        # nos padrões — senão o aviso pode discordar da prévia logo acima.
        "nao_coube": receitas.nao_couberam(
            template,
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
        return jsonify({"erro": _t("erro_modelo_sumido")}), 404
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
        return jsonify({"erro": _t("erro_modelo_invalido") % erro}), 400

    problemas = esquema.validar(template)
    if problemas:
        return jsonify({"erro": _t("erro_modelo_problemas"), "problemas": problemas}), 400

    limite = cobranca.plano(_plano_de(loja))["templates"]
    if limite and tabela_modelos.quantos(loja["id"]) >= limite:
        return jsonify({"erro": _t("erro_limite_modelos") % limite,
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
    """O plano da loja, reconferido com o Shopify quando o cache vence.

    O Shopify é a fonte da verdade sobre pagamento; o nosso banco é só cache.
    O webhook avisa quando muda, e esta função é quem vai buscar o valor novo —
    **na hora em que ele é necessário**, não dentro do webhook, que precisa
    responder rápido.

    ## Se o Shopify não responder, o lojista NÃO perde acesso

    A tentação é cair pro grátis quando a consulta falha. Isso significaria que
    uma instabilidade do Shopify tira o recurso pago de quem está pagando, no
    meio do trabalho. O contrário — alguém que cancelou manter acesso por mais
    algumas horas — custa muito menos.

    Por isso a falha mantém o último plano conhecido e só adia a próxima
    tentativa. Adiar é de propósito: sem isso, cada requisição tentaria de novo
    e uma queda do Shopify viraria lentidão em tudo.
    """
    plano = loja["plano"] if loja["plano"] in cobranca.PLANOS else "gratis"

    if not tabela_lojas.plano_venceu(loja):
        return plano

    try:
        # Uma tentativa só. Isto roda DENTRO de um pedido de impressão, e o
        # padrão de 3 tentativas com espera pode levar até 63 segundos — o
        # lojista ficaria olhando um botão travado por causa de uma atualização
        # de cache que pode muito bem esperar as próximas horas.
        resposta = rede.graphql(loja["dominio"], loja["token"],
                                {"query": cobranca.CONSULTA_ASSINATURA},
                                tentativas=1)
        plano = cobranca.plano_ativo(resposta)
    except (rede.ErroDeRede, KeyError, ValueError) as erro:
        current_app.logger.warning(
            "não consegui reconferir o plano da loja; mantendo %r: %s", plano, erro)

    tabela_lojas.marcar_plano(loja["id"], plano)
    return plano


@rotas.post("/imprimir")
@exige_loja
def imprimir(loja):
    dados = request.get_json(silent=True) or {}
    motor = (dados.get("motor") or "pdf").lower()
    itens = dados.get("itens") or []

    if not isinstance(itens, list) or not itens:
        return jsonify({"erro": _t("erro_sem_itens")}), 400

    plano = _plano_de(loja)

    if motor not in ("pdf", "zpl"):
        return jsonify({"erro": _t("erro_motor") % motor}), 400
    if not cobranca.pode_usar(plano, motor):
        return jsonify({"erro": _t("erro_motor_bloqueado"),
                        "motivo": "motor_bloqueado"}), 402

    fila, quantas = _fila(itens)
    if quantas > TETO_POR_VEZ:
        return jsonify({"erro": _t("erro_lote_grande") % (quantas, TETO_POR_VEZ),
                        "motivo": "lote_grande"}), 400

    ja_foram = impressoes.no_mes(loja["id"])
    if not cobranca.dentro_do_limite(plano, ja_foram + quantas):
        limite = cobranca.plano(plano)["limite_etiquetas_mes"]
        return jsonify({"erro": _t("erro_limite_mes") % (ja_foram, limite),
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
        return jsonify({"erro": _t("erro_escolha_modelo")}), 400

    if motor == "zpl":
        saida = motor_zpl.render_lote(template, fila,
                                      dpi=int(dados.get("dpi") or 203))
        impressoes.registrar(loja["id"], quantas, motor, modelo_id)
        return current_app.response_class(saida, mimetype="text/plain; charset=utf-8")

    buffer = io.BytesIO(motor_pdf.render(template, fila))
    impressoes.registrar(loja["id"], quantas, motor, modelo_id)
    return send_file(buffer, mimetype="application/pdf",
                     as_attachment=True, download_name="etiquetas.pdf")


# ------------------------------------------------------------------ cobrança

@rotas.post("/assinar")
@exige_loja
def assinar(loja):
    """Cria a assinatura no Shopify e devolve pra onde mandar o lojista.

    A cobrança entra na fatura que ele já paga: sem cartão, sem checkout, sem
    criar conta em lugar nenhum. É a maior vantagem de cobrar por aqui, e é por
    isso que a gente não montou pagamento próprio.

    Esta rota **não libera nada**. Ela só pede a assinatura; quem confirma é o
    lojista, na tela do Shopify, e quem diz que ela existe é o Shopify quando o
    `_plano_de` for reconferir. Liberar aqui seria acreditar num clique.
    """
    dados = request.get_json(silent=True) or {}
    codigo = str(dados.get("plano") or "pro")

    # Validar o pedido ANTES de ir à rede. Plano que não existe, ou o grátis
    # (que não tem assinatura pra criar), são erro de quem chamou — recusar isso
    # depois de uma ida ao Shopify gasta chamada à toa e transforma um 400 claro
    # num 502 confuso quando a rede falha.
    try:
        cobranca.corpo_para_assinar(codigo, "https://validacao")
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400

    # Pergunta ao Shopify que tipo de loja é esta, em vez de depender de alguém
    # ter lembrado de trocar uma variável antes de publicar. Loja de
    # desenvolvimento só aceita cobrança de teste; loja de verdade precisa da
    # cobrança de verdade.
    try:
        tipo = cobranca.e_loja_de_desenvolvimento(
            rede.graphql(loja["dominio"], loja["token"],
                         {"query": cobranca.CONSULTA_TIPO_DE_LOJA},
                         tentativas=1))
    except rede.ErroDeRede as erro:
        return jsonify({"erro": str(erro)}), 502

    if tipo is None:
        # Sem saber o tipo, não dá pra decidir. Errar pra qualquer lado custa
        # caro: cobrança real em loja de teste é reprovação, e cobrança de teste
        # em loja real é entregar o produto de graça sem ninguém perceber.
        current_app.logger.error(
            "não consegui saber se a loja é de desenvolvimento; assinatura recusada")
        return jsonify({"erro": _t("erro_assinatura_recusada")}), 502

    try:
        corpo = cobranca.corpo_para_assinar(
            codigo,
            "%s/cobranca/volta?shop=%s" % (config.URL_DO_APP, loja["dominio"]),
            desenvolvimento=tipo)
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400

    try:
        resposta = rede.graphql(loja["dominio"], loja["token"], corpo)
    except rede.ErroDeRede as erro:
        return jsonify({"erro": str(erro)}), 502

    erros = catalogo.erros_do_graphql(resposta)
    if erros:
        current_app.logger.warning("assinatura recusada: %s", "; ".join(erros))
        return jsonify({"erro": _t("erro_assinatura_recusada"),
                        "detalhes": erros}), 502

    try:
        # `userErrors` vem DENTRO de uma resposta 200. Sem isto o lojista seria
        # mandado pra lugar nenhum achando que assinou.
        url = cobranca.url_de_confirmacao(resposta)
    except ValueError as erro:
        current_app.logger.warning("assinatura sem URL de confirmação: %s", erro)
        return jsonify({"erro": str(erro)}), 502

    return jsonify({"url": url, "teste": tipo})


@rotas.get("/planos")
@exige_loja
def planos(loja):
    """Os planos, pra tela montar a comparação sem repetir os preços no JS."""
    atual = _plano_de(loja)
    return jsonify({
        "atual": atual,
        "dias_de_teste": cobranca.DIAS_DE_TESTE,
        "planos": [{
            "codigo": c, "nome": _t("plano_%s_nome" % c), "preco_usd": p["preco_usd"],
            "resumo": _t("plano_%s_resumo" % c),
            "limite_etiquetas_mes": p["limite_etiquetas_mes"],
            "templates": p["templates"], "motores": list(p["motores"]),
        } for c, p in cobranca.PLANOS.items()],
    })


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
        "nome_do_plano": _t("plano_%s_nome" % plano),
        "etiquetas_no_mes": impressoes.no_mes(loja["id"]),
        "limite_mes": detalhes["limite_etiquetas_mes"],
        "modelos": tabela_modelos.quantos(loja["id"]),
        "limite_modelos": detalhes["templates"],
        "motores": list(detalhes["motores"]),
    })
