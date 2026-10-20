"""Ler o catálogo da loja e traduzir pro formato que o motor entende.

Duas responsabilidades, e é importante que sejam duas:

**Montar a consulta GraphQL.** Texto puro, sem rede.

**Traduzir a resposta** do formato do Shopify pro dicionário que `campos.py`
resolve.

A tradução mora aqui e em nenhum outro lugar. Se cada tela ler o JSON do Shopify
por conta própria, o dia em que a API mudar um nome de campo vira uma caçada por
todo o projeto — e algum canto vai ficar pra trás.

## O que a gente NÃO pede

Sem pedido, sem cliente, sem endereço. Um app de etiqueta não tem por que
enxergar quem comprou, e cada campo a mais é uma pergunta a mais na revisão do
Shopify e um dado a mais pra vazar se algo der errado.
"""

VERSAO_API = "2026-07"

# A consulta é escrita por extenso, com paginação por cursor. Loja com 8 mil
# produtos não cabe numa resposta só, e o Shopify limita o tamanho da página.
CONSULTA_PRODUTOS = """
query produtos($quantos: Int!, $depois: String, $busca: String) {
  products(first: $quantos, after: $depois, query: $busca) {
    pageInfo { hasNextPage endCursor }
    nodes {
      id
      title
      vendor
      productType
      onlineStoreUrl
      variants(first: 100) {
        pageInfo { hasNextPage }
        nodes {
          id
          title
          sku
          barcode
          price
          compareAtPrice
          inventoryQuantity
        }
      }
    }
  }
}
""".strip()

CONSULTA_LOJA = """
query { shop { name myshopifyDomain currencyCode } }
""".strip()


def url_graphql(loja: str) -> str:
    from . import dominio
    return dominio.url_admin(loja, VERSAO_API, "graphql.json")


def consulta_de_produtos(quantos=50, depois=None, busca=None) -> dict:
    """O corpo da requisição. Sem rede: quem chama executa.

    `quantos` é limitado a 250 porque é o teto do Shopify — pedir mais devolve
    erro, e descobrir isso em produção é irritante.
    """
    return {
        "query": CONSULTA_PRODUTOS,
        "variables": {
            "quantos": max(1, min(250, int(quantos))),
            "depois": depois,
            "busca": busca,
        },
    }


def _texto(valor) -> str:
    return "" if valor is None else str(valor)


def para_etiquetas(resposta: dict, nome_da_loja: str = "") -> list:
    """Resposta do Shopify → lista de dicionários que o motor entende.

    Cada VARIANTE vira uma etiqueta, não cada produto. É a variante que tem SKU,
    código de barras e preço próprios — etiquetar "Camiseta" sem dizer que é a
    azul tamanho M não serve pra nada numa prateleira.

    Resposta torta não derruba: campo que falta vira vazio, produto quebrado é
    pulado. Uma loja com 8 mil produtos sempre tem algum cadastro estranho, e
    perder a fila inteira por causa dele seria o pior desfecho.
    """
    saida = []
    dados = (resposta or {}).get("data") or {}
    produtos = (dados.get("products") or {}).get("nodes") or []

    for produto in produtos:
        if not isinstance(produto, dict):
            continue
        bloco = produto.get("variants") or {}
        variantes = bloco.get("nodes") or []
        # Produto com mais de 100 variantes tem o resto cortado pela consulta.
        # É raro (grade de roupa grande chega lá), e sumir em silêncio seria o
        # lojista imprimir a prateleira faltando tamanhos sem saber por quê.
        # Melhor dizer, e deixar a tela avisar.
        cortado = bool((bloco.get("pageInfo") or {}).get("hasNextPage"))
        for variante in variantes:
            if not isinstance(variante, dict):
                continue
            saida.append({
                "produto": {
                    # O id entra porque a mutação de escrita é por PRODUTO, não
                    # por variante — ver `loja/escrita.py`. Ele não vai pra
                    # etiqueta; `campos.py` nem o conhece.
                    "id": _texto(produto.get("id")),
                    "titulo": _texto(produto.get("title")),
                    "fornecedor": _texto(produto.get("vendor")),
                    "tipo": _texto(produto.get("productType")),
                    "url": _texto(produto.get("onlineStoreUrl")),
                },
                "variante": {
                    "id": _texto(variante.get("id")),
                    "titulo": _texto(variante.get("title")),
                    "sku": _texto(variante.get("sku")),
                    "codigo_barras": _texto(variante.get("barcode")),
                    "preco": _texto(variante.get("price")),
                    "preco_comparado": _texto(variante.get("compareAtPrice")),
                    # Não vai pra etiqueta: serve pra sugerir QUANTAS imprimir.
                    "estoque": variante.get("inventoryQuantity"),
                    "url": _texto(produto.get("onlineStoreUrl")),
                },
                "loja": {"nome": nome_da_loja},
                # Não vai pra etiqueta: é aviso pra tela.
                "variantes_cortadas": cortado,
            })
    return saida


# Os filtros de "o que está faltando no cadastro". Existem como função pura,
# separada da rota, porque são a regra — e porque a rota tem rede no meio.
#
# Isto é o destaque nº 5 da ficha do líder do nicho ("Identifique instantaneamente
# produtos sem códigos de barras ou SKUs"), e é o passo zero de quem vai gerar:
# antes de criar código pra alguém, mostrar PRA QUEM falta.
FILTROS = {
    "sem_codigo": lambda it: not _texto(
        (it.get("variante") or {}).get("codigo_barras")).strip(),
    "sem_sku": lambda it: not _texto(
        (it.get("variante") or {}).get("sku")).strip(),
    # Serve pro gerador: um item que não tem nem um nem outro é o caso mais
    # urgente, e é o que o lojista quer ver primeiro.
    "sem_nenhum": lambda it: (
        not _texto((it.get("variante") or {}).get("codigo_barras")).strip()
        and not _texto((it.get("variante") or {}).get("sku")).strip()),
}


def filtrar(itens, filtro: str) -> list:
    """Aplica o filtro. Filtro desconhecido ou vazio devolve tudo.

    Desconhecido NÃO levanta erro de propósito: isto vem da querystring, e uma
    tela antiga mandando um nome que não existe mais deve mostrar o catálogo
    inteiro, não uma tela de erro.
    """
    regra = FILTROS.get(filtro or "")
    return [i for i in (itens or []) if regra(i)] if regra else list(itens or [])


def produtos_com_variantes_cortadas(itens) -> list:
    """Os produtos que tinham mais variantes do que a consulta trouxe."""
    vistos = []
    for item in itens or []:
        if item.get("variantes_cortadas"):
            titulo = (item.get("produto") or {}).get("titulo") or ""
            if titulo not in vistos:
                vistos.append(titulo)
    return vistos


def tem_proxima_pagina(resposta: dict) -> tuple:
    """(tem_mais, cursor). O cursor volta na próxima chamada."""
    dados = (resposta or {}).get("data") or {}
    info = (dados.get("products") or {}).get("pageInfo") or {}
    return bool(info.get("hasNextPage")), info.get("endCursor")


def quantidade_sugerida(item: dict) -> int:
    """Quantas etiquetas imprimir deste item, por padrão.

    É o estoque. Recebeu 40 unidades, quer 40 etiquetas — e essa é literalmente
    a reclamação do app oficial, onde o lojista digita "1" duas mil vezes.

    Estoque negativo (venda a descoberto) ou ausente vira 1: melhor imprimir uma
    a menos do que a pessoa não entender por que saiu nada.
    """
    estoque = (item.get("variante") or {}).get("estoque")
    try:
        return max(1, int(estoque))
    except (TypeError, ValueError):
        return 1


def erros_do_graphql(resposta: dict) -> list:
    """Os erros que o Shopify devolve DENTRO de uma resposta 200.

    GraphQL responde 200 mesmo quando falhou, com os problemas num campo
    `errors`. Quem só olha o código HTTP acha que deu tudo certo e mostra uma
    tela vazia pro lojista, sem explicação.
    """
    erros = (resposta or {}).get("errors") or []
    return [str(e.get("message", e)) if isinstance(e, dict) else str(e)
            for e in erros]
