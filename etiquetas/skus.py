"""Gera SKU por regra. O passo mais barato do gerador — e o mais honesto.

SKU **não tem norma**: não existe autoridade de numeração, não existe dígito
verificador, não existe faixa reservada. É um código interno da loja, e isso quer
dizer que a gente pode gerar sem mentir para ninguém.

Isso é o oposto do código de barras, onde cada número pertence a alguma faixa com
dono — ver `docs/gerador-de-codigo.md`.

## Por que isto é módulo separado, sem rede e sem banco

A regra "molde + produto → texto" é uma função pura. Separada, ela é testável
sem loja, sem token e sem escopo de escrita: dá para ver a tabela inteira que
*seria* gravada antes de o app pedir qualquer permissão nova ao lojista.

É a mesma ideia da prévia da etiqueta: **mostrar antes de fazer.**

## As duas regras que vêm de fora e não se discutem aqui

**Nunca sobrescrever SKU que já existe.** Um SKU em uso está em planilha, em
etiqueta impressa e na cabeça de quem trabalha na loja. Trocar quebra tudo isso
de uma vez, e em silêncio.

**Nunca repetir SKU dentro da mesma loja.** SKU repetido faz o lojista pegar o
produto errado no estoque — e, se virar código de barras depois, bipa errado no
caixa.
"""
import re
import unicodedata

from . import campos

# O que dá pra usar no molde, e de onde cada peça sai.
#
# A lista é curta de propósito: molde com dez peças ninguém consegue ler depois,
# e SKU longo não cabe na etiqueta pequena, que é justamente onde ele é mais
# necessário.
PECAS = {
    "fornecedor": "produto.fornecedor",
    "tipo": "produto.tipo",
    "titulo": "produto.titulo",
    "variante": "variante.titulo",
}

# O `{titulo}` está aqui porque ele é a peça que diz QUAL produto é. Tipo é
# categoria; fornecedor é quem vendeu. Sem o título, o SKU não identifica nada.
#
# MEDIDO numa loja de verdade em 20/10/2026. O padrão era
# `{fornecedor}-{tipo}-{variante}`, e numa loja que não preenche "tipo" e tem
# produtos sem variante ele produzia isto:
#
#     The Minimal Snowboard   ->  ETIK          (só o fornecedor)
#     The Archived Snowboard  ->  SNOW-SNOW     (fornecedor e tipo iguais)
#
# `ETIK` sozinho é pior que inútil: o próximo produto da mesma loja vira
# `ETIK-2`. Com o título, os mesmos produtos saem `ETIK-MINI` e `SNOW-ARCH`, e
# o número de colisões caiu de 4 para 2 em 16.
#
# Sem `{seq}` de propósito: com título e variante o SKU já sai único na maioria
# dos casos, e a sequência viraria `0001` em todos. Quem colidir ganha sufixo,
# é avisado na linha, e o resumo diz quantas foram — aí quem quiser numerar
# acrescenta `{seq}` sabendo por quê.
MOLDE_PADRAO = "{fornecedor}-{titulo}-{variante}"

# Quantas letras de cada peça entram. Quatro é o que ainda dá pra reconhecer
# ("CAMI" é camiseta, "CAM" podia ser câmera) sem estourar a largura da etiqueta.
LETRAS_POR_PECA = 4

# Quantos dígitos tem a sequência. Quatro aguenta 9.999 itens no mesmo grupo, que
# é mais do que qualquer loja pequena vai ter de uma combinação só.
DIGITOS_DA_SEQUENCIA = 4

# Teto do SKU inteiro. Acima disso ele não cabe na etiqueta de joia nem vira um
# Code 128 legível numa 5167 — e SKU que não cabe é SKU que não serve.
TAMANHO_MAXIMO = 32


# O que o Shopify põe no título da variante quando o produto NÃO TEM variante.
# Não é nome de nada, e cada letra dele no SKU é ruído.
#
# MEDIDO numa loja de verdade em 20/10/2026: com o molde padrão, 13 de 23
# produtos viravam algo terminado em `-DEFA`. Além de não dizer nada, isso
# fazia produtos diferentes colidirem e ganharem sufixo `-2`, `-3`.
#
# A constante do Shopify é literal e em inglês, independente do idioma da loja.
SEM_VARIANTE = "default title"


def normalizar_variante(texto: str, letras: int = LETRAS_POR_PECA) -> str:
    """A variante preservando a estrutura que o Shopify já deu.

    O título de variante vem como `"M / Preto"` — duas opções separadas por
    barra. Medindo, a primeira versão disto colava tudo e devolvia `MPRE`, que
    não dá pra ler. Cada opção vira uma peça, e elas ficam separadas:

        "M / Preto"  ->  M-PRE
        "P / Azul Marinho"  ->  P-AZUL
        "Default Title"  ->  (nada)
    """
    if str(texto or "").strip().lower() == SEM_VARIANTE:
        return ""
    partes = [normalizar(p, letras) for p in str(texto or "").split("/")]
    return "-".join(x for x in partes if x)


# Artigos que começam título de produto e não distinguem nada.
#
# MEDIDO numa loja de verdade: com 4 letras, "The Minimal Snowboard" virava
# `THEM` e "The Complete Snowboard" virava `THEC`. O artigo comia quase todo o
# orçamento de letras, e três produtos diferentes ("The Collection Snowboard:
# Hydrogen", "...: Oxygen", "...: Liquid") viravam o MESMO `THEC`, precisando
# de sufixo `-2` e `-3` pra se distinguir.
#
# Só artigo, e só no COMEÇO. Preposição ("de", "da") fica: ela aparece no meio
# de nome próprio com frequência, e tirar faria mais estrago que bem.
ARTIGOS = {"the", "a", "an", "o", "os", "as", "um", "uma", "uns", "umas"}


def normalizar(texto: str, letras: int = LETRAS_POR_PECA) -> str:
    """Um pedaço de texto virando peça de SKU.

    Tira acento, descarta artigo do começo, tira o que não é letra ou número,
    deixa maiúsculo e corta.

    O acento sai por motivo prático, não estético: este texto vai parar num
    Code 128 e numa etiqueta impressa por fonte de impressora térmica, onde "ç"
    e "ã" viram lixo ou sumem. Melhor "ACAI" que "AÇAÍ" ilegível.
    """
    if not texto:
        return ""
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFD", str(texto))
        if unicodedata.category(c) != "Mn")

    # Separa em palavras ANTES de cortar: colar tudo primeiro é o que fazia o
    # artigo consumir as letras que deviam identificar o produto.
    palavras = [p for p in re.split(r"[^0-9A-Za-z]+", sem_acento) if p]
    corte = max(1, letras)

    # Só descarta o artigo se o que SOBRA ainda enche uma peça inteira.
    #
    # Sem essa condição, "A/B C-1" virava `BC1` — o "A" ali não é artigo, é
    # parte do valor. O mesmo valeria pra "A 200": descartar um "A" que
    # distingue o produto é pior que manter um artigo que não distingue.
    #
    # Com a condição, "A Casa do Pão" ainda vira CASA (sobram 9 letras) e
    # "A 200" continua A200 (sobrariam 3).
    while (len(palavras) > 1 and palavras[0].lower() in ARTIGOS
           and len("".join(palavras[1:])) >= corte):
        palavras.pop(0)

    return "".join(palavras).upper()[:corte]


def _juntar(molde: str, pecas: dict) -> str:
    """Preenche o molde e costura as emendas que ficaram vazias.

    Peça vazia é rotina — produto sem fornecedor, variante sem título. Sem esta
    limpeza o SKU sairia `ACME--M-0001` ou `-CAM-M-0001`, que é feio e, pior,
    faz dois produtos diferentes virarem o mesmo SKU quando as duas peças que
    faltam são outras.
    """
    saida = molde
    for nome, valor in pecas.items():
        saida = saida.replace("{%s}" % nome, valor)
    # Separador repetido vira um só, e sobra nas pontas sai fora.
    saida = re.sub(r"[-_.]{2,}", "-", saida)
    return saida.strip("-_.")


def montar(molde: str, dados: dict, sequencia: int = 1,
           letras: int = LETRAS_POR_PECA,
           digitos: int = DIGITOS_DA_SEQUENCIA) -> str:
    """Molde + um produto + um número → o SKU.

    Função pura: mesmo molde e mesmo produto dão sempre o mesmo texto. É isso
    que permite mostrar a tabela inteira ao lojista antes de gravar qualquer
    coisa.
    """
    pecas = {}
    for nome, caminho in PECAS.items():
        bruto = campos.resolver(caminho, dados)
        pecas[nome] = (normalizar_variante(bruto, letras) if nome == "variante"
                       else normalizar(bruto, letras))
    pecas["seq"] = str(max(0, int(sequencia))).zfill(max(1, digitos))
    return _juntar(molde or MOLDE_PADRAO, pecas)[:TAMANHO_MAXIMO]


def conferir_molde(molde: str) -> list:
    """Problemas do molde, todos de uma vez. Lista vazia = pode usar."""
    problemas = []
    molde = (molde or "").strip()
    if not molde:
        return ["o molde está vazio"]

    usadas = set(re.findall(r"\{(\w+)\}", molde))
    desconhecidas = sorted(usadas - set(PECAS) - {"seq"})
    if desconhecidas:
        problemas.append(
            "o molde usa %s, que não existe. Disponíveis: %s"
            % (", ".join("{%s}" % p for p in desconhecidas),
               ", ".join("{%s}" % p for p in sorted(PECAS) + ["seq"])))

    # `{seq}` NÃO é obrigatória, e exigir foi erro da primeira versão.
    #
    # Medindo: com `{variante}` no molde, cada item já virava seu próprio grupo,
    # e a sequência saía `0001` em todos. Ou seja, ela não desambiguava nada —
    # só sujava o SKU com quatro dígitos iguais.
    #
    # Quando o molde não tem `{seq}` e dois itens colidem, o `gerar_lote`
    # acrescenta um sufixo e DIZ que acrescentou. Melhor um número que aparece
    # só onde foi preciso do que um que aparece em tudo.
    if not (usadas - {"seq"}):
        problemas.append("o molde só tem número — acrescente ao menos uma peça "
                         "de texto, senão o SKU não diz nada sobre o produto")
    return problemas


def _grupo(molde: str, item: dict, letras: int, digitos: int) -> str:
    """O SKU sem a sequência. É por aqui que a numeração conta."""
    base = montar(molde, item, 0, letras, digitos)
    return base[:-digitos] if digitos and "{seq}" in molde else base


def gerar_lote(itens, molde: str = MOLDE_PADRAO, ja_usados=None,
               letras: int = LETRAS_POR_PECA,
               digitos: int = DIGITOS_DA_SEQUENCIA) -> list:
    """O lote inteiro, com o motivo de cada um que ficou de fora.

    Devolve uma linha por item, sempre na ordem recebida, no formato
    `{"item": ..., "sku": "...", "pulado": "motivo"}`. Quem pula nunca some em
    silêncio — é a mesma regra da prévia da etiqueta, que diz por que o código
    não apareceu.

    `ja_usados` são os SKUs que a loja já tem. Eles entram na conferência de
    colisão, senão o gerador criaria um SKU que já pertence a outro produto.
    """
    problemas = conferir_molde(molde)
    if problemas:
        raise ValueError("; ".join(problemas))

    usados = {str(s).strip().upper() for s in (ja_usados or ()) if str(s).strip()}
    # A sequência conta por GRUPO, não pela loja inteira: o lojista espera
    # ACME-CAMI-P-0001 e ACME-CAMI-M-0002 se seguirem, e não pularem porque
    # outro fornecedor entrou no meio.
    contador = {}
    saida = []

    for item in itens or []:
        atual = campos.resolver("variante.sku", item).strip()
        if atual:
            # Regra que vem de fora e não se discute: SKU em uso está em
            # planilha, em etiqueta já impressa e na cabeça de quem trabalha ali.
            saida.append({"item": item, "sku": atual, "pulado": "já tem SKU"})
            continue

        com_seq = "{seq}" in molde
        n = contador.get(_grupo(molde, item, letras, digitos), 0)

        sku, aviso = "", ""
        # Anda até achar um livre. O teto evita laço infinito se o molde gerar
        # sempre a mesma coisa.
        for tentativa in range(1, 10000):
            if com_seq:
                n += 1
                candidato = montar(molde, item, n, letras, digitos)
            else:
                # Sem `{seq}` no molde o nome sai limpo; só quem colide ganha
                # sufixo, e o lojista é avisado de que ganhou.
                base = montar(molde, item, 0, letras, digitos)
                candidato = base if tentativa == 1 else "%s-%d" % (base, tentativa)
                if tentativa > 1:
                    aviso = "repetia outro SKU, então ganhou o sufixo -%d" % tentativa
            if candidato and candidato.upper() not in usados:
                sku = candidato
                break
        if com_seq:
            contador[_grupo(molde, item, letras, digitos)] = n

        # SKU que é só número não serve: ele não diz nada sobre o produto, e o
        # lojista não consegue achar nada com ele. Acontece de verdade — produto
        # sem fornecedor, sem tipo e sem variante existe em catálogo importado.
        if not sku or not any(c.isalpha() for c in sku):
            saida.append({"item": item, "sku": "", "pulado":
                          "este produto não tem fornecedor, tipo nem variante — "
                          "não há texto para montar um SKU que signifique algo"})
            continue

        usados.add(sku.upper())
        saida.append({"item": item, "sku": sku, "pulado": "", "aviso": aviso})

    return saida
