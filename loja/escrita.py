"""As mutações que ESCREVEM no catálogo do lojista. Só monta; não executa.

Mesma escolha do resto de `loja/`: devolve (corpo da consulta) e deixa a rede
pro `rede.py`. Assim isto é testável sem token, sem loja e sem escopo.

## É o único arquivo do projeto que pede permissão de escrita

Até aqui o app pedia dois escopos, os dois de leitura, e isso era a frase da
ficha que nenhum concorrente podia escrever. Gerar SKU e código de barras custa
essa frase — ver `docs/gerador-de-codigo.md`.

Por isso aqui é o lugar mais cuidadoso do projeto: um defeito nestas linhas mexe
no catálogo de quem paga, não num papel.

## Três coisas da API que custaram pesquisa e se esquecem

**Não existe campo `sku` na variante.** Ele mora em `inventoryItem.sku`. Mandar
`sku` direto é erro de esquema, e a mensagem do Shopify não ajuda.

**O campo `barcode` está OBSOLETO.** O atual é `barcodes`, uma lista. Quando
chegar o gerador de código de barras, é por lá — e não dá pra mandar os dois na
mesma variante.

**A mutação é por PRODUTO, não por variante.** `productVariantsBulkUpdate` leva
um `productId` e a lista de variantes dele. Então um lote de 40 SKUs espalhados
em 15 produtos são 15 chamadas, não uma.
"""

# `allowPartialUpdates` fica no padrão (false) de propósito: ou o produto
# inteiro grava, ou nenhuma variante dele grava.
#
# Parece menos tolerante, e é — mas é o que mantém o desfazer exato. Com
# atualização parcial, metade das variantes de um produto gravaria e a outra
# metade não, e o registro teria que adivinhar quais. Produto que falha é
# relatado ao lojista e tentado de novo; registro de desfazer errado não tem
# conserto.
MUTACAO_VARIANTES = """
mutation gravar($produto: ID!, $variantes: [ProductVariantsBulkInput!]!) {
  productVariantsBulkUpdate(productId: $produto, variants: $variantes) {
    productVariants {
      id
      sku
    }
    userErrors {
      field
      message
    }
  }
}
""".strip()


def agrupar_por_produto(mudancas) -> dict:
    """[(produto_id, variante_id, valor)] → {produto_id: [(variante_id, valor)]}.

    Existe porque a mutação é por produto. A ordem dentro de cada produto é
    preservada pra a tabela que o lojista conferiu na tela bater com o que foi
    gravado.
    """
    grupos = {}
    for produto_id, variante_id, valor in (mudancas or []):
        p, v = str(produto_id or "").strip(), str(variante_id or "").strip()
        if not p or not v:
            # Linha sem id não vira escrita silenciosa: é dado torto vindo da
            # tela, e gravar "no produto nenhum" seria pior que pular.
            continue
        grupos.setdefault(p, []).append((v, str(valor or "")))
    return grupos


def consulta_de_skus(produto_id: str, pares) -> dict:
    """O corpo da chamada que grava os SKUs de UM produto.

    `pares` é [(variante_id, sku)].
    """
    if not str(produto_id or "").strip():
        raise ValueError("não dá pra gravar sem o id do produto")
    variantes = [{"id": str(v), "inventoryItem": {"sku": str(sku or "")}}
                 for v, sku in (pares or []) if str(v or "").strip()]
    if not variantes:
        raise ValueError("não há variante nenhuma para gravar")
    return {
        "query": MUTACAO_VARIANTES,
        "variables": {"produto": str(produto_id), "variantes": variantes},
    }


def erros_da_escrita(resposta: dict) -> list:
    """Os motivos de recusa, em texto. Lista vazia = gravou.

    O Shopify responde **200 com erro dentro** em duas camadas diferentes:
    `errors` no topo (consulta malformada) e `userErrors` dentro da mutação
    (recusa de negócio, tipo SKU duplicado). Olhar só uma delas é o jeito
    clássico de achar que gravou quando não gravou.
    """
    if not isinstance(resposta, dict):
        return ["resposta do Shopify em formato inesperado"]

    motivos = []
    for erro in resposta.get("errors") or []:
        if isinstance(erro, dict) and erro.get("message"):
            motivos.append(str(erro["message"]))

    dados = (resposta.get("data") or {}).get("productVariantsBulkUpdate") or {}
    for erro in dados.get("userErrors") or []:
        if not isinstance(erro, dict):
            continue
        campo = ".".join(str(c) for c in (erro.get("field") or []) if c)
        texto = str(erro.get("message") or "recusado sem motivo informado")
        motivos.append("%s: %s" % (campo, texto) if campo else texto)
    return motivos


def variantes_gravadas(resposta: dict) -> dict:
    """{variante_id: sku} do que o Shopify CONFIRMOU ter gravado.

    O registro de desfazer sai daqui, e não da lista que a gente mandou. São
    coisas diferentes: mandar não é gravar, e anotar "desfazer" para algo que
    não aconteceu faria o desfazer sobrescrever um valor alheio.
    """
    dados = (resposta or {}).get("data") or {}
    bloco = dados.get("productVariantsBulkUpdate") or {}
    saida = {}
    for v in bloco.get("productVariants") or []:
        if isinstance(v, dict) and v.get("id"):
            saida[str(v["id"])] = str(v.get("sku") or "")
    return saida
