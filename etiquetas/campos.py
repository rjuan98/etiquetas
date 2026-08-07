"""Resolve "produto.titulo" no valor de verdade. O único resolvedor do projeto.

Existe sozinho por dois motivos.

O primeiro é o de sempre: se cada motor souber ler campo por conta própria, os
três vão divergir e algum vai formatar diferente. Foi o que aconteceu no Hércules
com o `fonte='ajuste'`, contado como gasto em metade das telas e ignorado na
outra metade.

O segundo é mais prático: acrescentar campo novo passa a ser acrescentar uma
linha aqui, em vez de caçar todos os lugares onde o dado é lido.

E a regra mais importante deste arquivo: **campo que falta nunca explode.** Uma
loja com 8 mil produtos vai ter produto sem código de barras, sem SKU e com
título vazio. Se o gerador quebrar no produto 4.312, o lojista perde a fila
inteira de impressão e não sabe por quê.
"""

# O que dá pra pôr numa etiqueta. Acrescentar campo é acrescentar uma linha.
CAMPOS = {
    "produto.titulo": ("produto", "titulo"),
    "produto.fornecedor": ("produto", "fornecedor"),
    "produto.tipo": ("produto", "tipo"),
    "variante.titulo": ("variante", "titulo"),
    "variante.sku": ("variante", "sku"),
    "variante.codigo_barras": ("variante", "codigo_barras"),
    "variante.preco": ("variante", "preco"),
    "variante.preco_comparado": ("variante", "preco_comparado"),
    "loja.nome": ("loja", "nome"),
    # O QR quase sempre aponta pra um endereço. Sem um campo de link ele vira
    # enfeite — dá pra codificar o SKU, mas ninguém aponta a câmera pra ler SKU.
    "produto.url": ("produto", "url"),
    "variante.url": ("variante", "url"),
}


def existe(caminho: str) -> bool:
    return caminho in CAMPOS


def disponiveis() -> list[str]:
    """Para o editor mostrar a lista do que dá pra arrastar pra etiqueta."""
    return sorted(CAMPOS)


def resolver(caminho: str, dados: dict) -> str:
    """Devolve o valor como texto. Nunca levanta exceção por dado faltando.

    Campo inexistente no catálogo levanta erro (é bug de template, e a gente quer
    saber). Campo que existe mas está vazio no produto devolve "" — porque isso
    não é bug, é a vida real de quem tem 8 mil produtos cadastrados às pressas.
    """
    if caminho not in CAMPOS:
        raise ValueError(
            "campo %r não existe. Disponíveis: %s" % (caminho, ", ".join(disponiveis()))
        )
    grupo, chave = CAMPOS[caminho]
    # `dados` vindo torto (None, lista, texto) não pode derrubar a impressão da
    # fila inteira — vira campo vazio, que é o mesmo tratamento de dado ausente.
    if not isinstance(dados, dict):
        return ""
    grupo_dados = dados.get(grupo)
    if not isinstance(grupo_dados, dict):
        return ""
    valor = grupo_dados.get(chave)
    if valor is None:
        return ""
    return str(valor)


def formatar_preco(valor, simbolo="R$", simbolo_depois=False,
                   decimal=",", milhar=".") -> str:
    """Formata dinheiro do jeito que o país da loja escreve.

    Nasceu de uma reclamação real: uma loja francesa não conseguia pôr o € à
    direita, porque o app oficial fixa o símbolo à esquerda. Aqui é configuração.

    Valor que não é número vira "" em vez de estourar — produto sem preço
    cadastrado existe, e não pode derrubar a impressão da fila inteira.
    """
    try:
        numero = float(str(valor).replace(",", "."))
    except (TypeError, ValueError):
        return ""

    # NaN e infinito passam pelo float() e viram "R$ nan," na etiqueta. Já
    # aconteceu antes: no projeto anterior, um extrato com infinito envenenou o
    # saldo pra "R$ -inf". `numero != numero` é o jeito de pegar NaN, que é o
    # único valor que não é igual a si mesmo.
    if numero != numero or numero in (float("inf"), float("-inf")):
        return ""

    inteiro, _, centavos = ("%.2f" % numero).partition(".")

    # Milhar de trás pra frente, de três em três.
    negativo = inteiro.startswith("-")
    if negativo:
        inteiro = inteiro[1:]
    partes = []
    while len(inteiro) > 3:
        partes.insert(0, inteiro[-3:])
        inteiro = inteiro[:-3]
    partes.insert(0, inteiro)
    inteiro = milhar.join(partes)
    if negativo:
        inteiro = "-" + inteiro

    numero_formatado = inteiro + decimal + centavos
    if not simbolo:
        return numero_formatado
    return (numero_formatado + " " + simbolo) if simbolo_depois else (simbolo + " " + numero_formatado)
