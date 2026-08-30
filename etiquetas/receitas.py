"""Escolhas do lojista → um `Template` montado. O que faz a tela ser usável.

## Por que isto existe

Um `Template` é uma lista de elementos com coordenada, largura, tamanho de fonte
e alinhamento. Ninguém que vende caneca quer preencher isso. O que a pessoa quer
dizer é *"etiqueta de 5×2,5cm, com título, SKU, preço e código de barras"* — e é
essa frase que este arquivo traduz.

## E por que ele mora no servidor, não no navegador

A tentação é montar o JSON do template em JavaScript, já que é lá que os botões
estão. Seria a mesma armadilha da prévia (ver `motores/svg.py`): a regra viraria
duas, e a que o lojista vê discordaria da que imprime.

Aqui a tela manda **preferências** — quais campos, que formato, como mostrar o
preço — e recebe um template pronto. O navegador não sabe o que é milímetro.

## O layout é orçamento de altura, não coordenada fixa

Um número fixo de milímetro funcionaria pra 5×2,5cm e quebraria na etiqueta de
joia (5,6×1,2cm) e na de envio (10×15cm). Então a altura é repartida de cima pra
baixo, e cada bloco pega o que precisa dentro do que sobrou.

Quando não cabe tudo, some de baixo pra cima — primeiro o fornecedor, depois o
código de barras encolhe até o mínimo que ainda bipa. **Etiqueta com código de
barras ilegível é pior que etiqueta sem código**, porque o defeito só aparece no
caixa, com fila.
"""
from . import codigos, formatos, unidades
from .modelo import Calibracao, CodigoBarras, Preco, Template, Texto

# Os campos que a tela oferece, na ordem em que aparecem na etiqueta. A chave é o
# que vai e volta pela API; o resto é como ele é desenhado.
CAMPOS = {
    "titulo":        {"nome": "Título do produto", "campo": "produto.titulo"},
    "variante":      {"nome": "Variação (cor, tamanho)", "campo": "variante.titulo"},
    "fornecedor":    {"nome": "Fornecedor", "campo": "produto.fornecedor"},
    "sku":           {"nome": "SKU", "campo": "variante.sku"},
    "preco":         {"nome": "Preço", "campo": "variante.preco"},
    "codigo_barras": {"nome": "Código de barras", "campo": "variante.codigo_barras"},
}

PADRAO = ("titulo", "sku", "preco", "codigo_barras")

# **Ordem de sobrevivência**, que é diferente da ordem de desenho.
#
# Quando não cabe tudo, alguém tem que sair — e a primeira versão disto cortava
# de baixo pra cima, na ordem visual. Numa etiqueta de joia (56×12mm) o resultado
# foi o título de duas linhas ocupando a etiqueta inteira e o código de barras
# sumindo. Numa etiqueta de código de barras.
#
# Então o que fica é decidido por importância, não por posição: o código primeiro,
# porque é o que a etiqueta existe pra levar; depois o preço, que é o que o
# cliente procura; e o título por último, porque quem está com o produto na mão
# já sabe o que é.
PRIORIDADE = ("codigo_barras", "preco", "sku", "titulo", "variante", "fornecedor")

# Ordem em que aparecem na etiqueta, de cima pra baixo.
ORDEM_VISUAL = ("titulo", "variante", "fornecedor", "sku", "preco", "codigo_barras")

# Altura mínima de barra que ainda bipa com folga em leitor de caixa. Abaixo
# disso o leitor precisa de mira boa e mão parada, que é o oposto de fila.
BARRA_MINIMA_MM = 6.0

# Largura de cada barra fina, em dots de impressora térmica. Dois dots a 203dpi
# dão 0,25mm, que é o mínimo confortável pra leitor de mão barato — um dot só
# depende de impressora bem regulada e de etiqueta que não borra.
MODULO_PADRAO_DOTS = 2

# O número legível embaixo do código ocupa espaço próprio no desenho do reportlab.
TEXTO_DO_CODIGO_MM = 2.6

# Folga entre o último texto e o topo do código de barras.
#
# A altura de linha põe a LINHA DE BASE no fim do bloco, e a letra desce abaixo
# dela — o "p" de "preço", o rabo do "y", o traço do hífen. Entre duas linhas de
# texto isso é normal e até desejável. Contra um código de barras, que é tinta
# sólida a partir do topo, a descida cai em cima das barras.
#
# Medido na etiqueta Avery com fornecedor ligado: SKU e preço com base em
# 12,581mm e o código começando em 12,581mm exatos. Sobrepunha meio milímetro.
# Apareceu numa captura de tela, não num teste — os testes de borda não pegavam
# porque tudo continuava DENTRO da etiqueta.
#
# A folga é PROPORCIONAL à fonte, não um número fixo. A primeira tentativa usou
# 0,7mm pra tudo: resolveu nas etiquetas pequenas e continuou colidindo na de
# 3x2 polegadas, onde a fonte é o dobro e a letra desce o dobro junto.
DESCIDA_DA_LETRA = 0.22        # quanto a letra passa da linha de base
FOLGA_MINIMA_MM = 0.4


def _limitar(valor, minimo, maximo):
    return max(minimo, min(maximo, valor))


def _mm_da_fonte(tamanho_pt: float) -> float:
    return tamanho_pt * 25.4 / 72


def montar(formato: str = "zebra_2x1",
           campos=PADRAO,
           simbolo: str = "R$",
           simbolo_depois: bool = False,
           separador_decimal: str = ",",
           separador_milhar: str = ".",
           rotulo_sku: bool = True,
           digitos_do_codigo: bool = True,
           simbologia: str = "EAN13",
           largura_mm: float = 0.0,
           altura_mm: float = 0.0,
           desvio_x_mm: float = 0.0,
           desvio_y_mm: float = 0.0,
           nome: str = "") -> Template:
    """Monta o template. Só recebe coisa que o lojista sabe responder."""
    # Medida livre não vem do catálogo: o lojista digitou. O resto do montador
    # não muda — ele já trabalhava só com largura e altura em milímetro.
    if formato == formatos.LIVRE:
        midia = formatos.midia_livre(largura_mm, altura_mm)
        nome_do_formato = "%.4gx%.4g" % (midia.largura_mm, midia.altura_mm)
    else:
        fmt = formatos.obter(formato)
        midia = fmt.novo()
        nome_do_formato = fmt.nome
    ligados = [c for c in CAMPOS if c in set(campos or ())]

    largura, altura = midia.largura_mm, midia.altura_mm

    # Margem horizontal mede pela largura, vertical mede pela ALTURA. Usar a
    # largura nas duas fazia a etiqueta de joia (56×12mm) gastar 37% da altura
    # em margem — a conta que serve pra uma etiqueta larga e baixa não é a mesma
    # nos dois eixos.
    margem_x = _limitar(largura * 0.04, 1.5, 3.0)
    margem_y = _limitar(altura * 0.06, 0.8, 2.5)
    util = largura - 2 * margem_x

    # Tamanhos de fonte proporcionais à etiqueta, com teto e piso. Sem o piso, a
    # etiqueta de joia sai com letra de 3pt que ninguém lê; sem o teto, a de
    # envio vira um cartaz.
    pt_titulo = _limitar(altura * 0.30, 5.0, 16.0)
    pt_normal = _limitar(altura * 0.22, 4.5, 11.0)

    linha_titulo = _mm_da_fonte(pt_titulo) * 1.15
    linha_normal = _mm_da_fonte(pt_normal) * 1.15

    # O preço sai maior de propósito: é o que o cliente procura na prateleira.
    # Mas isso cria um problema de tipografia — dois textos de tamanhos
    # diferentes com o MESMO TOPO ficam desalinhados, porque a linha de base do
    # maior cai mais baixo. Na etiqueta de varejo dava 0,34mm de queda no preço,
    # o bastante pra parecer torto.
    #
    # A linha inteira mede o mais alto, e os dois são apoiados na MESMA BASE.
    pt_preco = pt_normal * 1.15
    linha_preco = _mm_da_fonte(pt_preco) * 1.15
    linha_valor = max(linha_normal, linha_preco)

    # Espaço pra letra do último texto descer sem encostar nas barras.
    folga_do_codigo = max(FOLGA_MINIMA_MM,
                          _mm_da_fonte(pt_preco) * (DESCIDA_DA_LETRA + 0.04))

    # Os dígitos impressos sob as barras custam 2,6mm de altura, e numa etiqueta
    # pequena esses 2,6mm são a diferença entre caber o SKU e não caber. Numa
    # Avery 5167 (44,45 × 12,7mm) a conta dava 0,07mm de falta — e o lojista
    # perdia o SKU sem nunca ter escolhido isso.
    #
    # Os dígitos repetem o que as barras já carregam; o SKU não está em nenhum
    # outro lugar da etiqueta. Mas eles são o plano B quando o leitor falha, e
    # essa troca é do lojista, não nossa: aqui só obedecemos.
    altura_dos_digitos = TEXTO_DO_CODIGO_MM if digitos_do_codigo else 0.0

    # --- 1. quem entra ------------------------------------------------------
    # O código de barras reserva o mínimo dele ANTES de o texto pegar espaço.
    # Sem essa reserva, o título come a etiqueta e a barra fica ilegível — e
    # barra ilegível só aparece no caixa, com fila.
    orcamento = altura - 2 * margem_y

    # Até aqui só a ALTURA era conferida, e por muito tempo isso bastou: nenhum
    # dos formatos do catálogo é estreito o suficiente pra um EAN-13 vazar. Uma
    # etiqueta de 1"×1" (25,4mm) é — o EAN-13 precisa de 28,3mm, e não é limite
    # nosso, é a norma: 95 módulos mais as duas zonas mudas.
    #
    # Sem esta conta, medida livre deixaria qualquer um digitar 20mm de largura e
    # receber um código serrado pela borda. Que é exatamente o defeito que este
    # app existe pra corrigir.
    largura_do_codigo = codigos.largura_minima_mm(
        codigos.obter(simbologia), MODULO_PADRAO_DOTS, unidades.ZEBRA_203,
        BARRA_MINIMA_MM)
    codigo_cabe_na_largura = margem_x + largura_do_codigo <= largura + 0.01

    entram = []
    for chave in PRIORIDADE:
        if chave not in ligados:
            continue
        if chave == "codigo_barras":
            if not codigo_cabe_na_largura:
                continue
            custo = BARRA_MINIMA_MM + altura_dos_digitos + folga_do_codigo
        elif chave in ("sku", "preco"):
            # Dividem a mesma linha: só o primeiro paga, e paga pela altura do
            # mais alto dos dois.
            custo = 0.0 if ("sku" in entram or "preco" in entram) else linha_valor
        elif chave == "titulo":
            custo = linha_titulo
        else:
            custo = linha_normal
        if orcamento - custo >= 0:
            entram.append(chave)
            orcamento -= custo

    # Título ganha a segunda linha só se sobrou espaço depois de todo o resto —
    # é um luxo, não uma reserva.
    titulo_em_2_linhas = "titulo" in entram and orcamento >= linha_titulo
    if titulo_em_2_linhas:
        orcamento -= linha_titulo

    # --- 2. onde cada um fica ------------------------------------------------
    elementos, y = [], margem_y
    tem_sku = "sku" in entram
    tem_preco = "preco" in entram
    metade = util / 2 if (tem_sku and tem_preco) else util
    linha_do_valor_feita = False
    y_da_linha = margem_y

    for chave in ORDEM_VISUAL:
        if chave not in entram:
            continue

        if chave == "titulo":
            linhas = 2 if titulo_em_2_linhas else 1
            elementos.append(Texto(
                campo="produto.titulo", x_mm=margem_x, y_mm=y, largura_mm=util,
                tamanho_pt=pt_titulo, linhas_max=linhas, negrito=True,
                excesso="cortar"))
            y += linha_titulo * linhas

        elif chave in ("variante", "fornecedor"):
            elementos.append(Texto(
                campo=CAMPOS[chave]["campo"], x_mm=margem_x, y_mm=y,
                largura_mm=util, tamanho_pt=pt_normal, linhas_max=1,
                excesso="cortar"))
            y += linha_normal

        elif chave in ("sku", "preco"):
            # SKU à esquerda e preço à direita, na MESMA linha. A largura é
            # dividida ao meio em vez de os dois competirem: SKU comprido
            # empurrando o preço pra fora da etiqueta é falha silenciosa.
            #
            # O `y` da linha é guardado ANTES de avançar. A primeira versão
            # avançava logo depois do SKU, e aí o preço — que vem em seguida na
            # ordem visual — nascia uma linha abaixo. No papel virava SKU e preço
            # desalinhados por 2,2mm, e nenhum teste de borda pegava, porque os
            # dois continuavam dentro da etiqueta. Apareceu olhando o ZPL cru.
            if not linha_do_valor_feita:
                y_da_linha = y
                y += linha_valor
                linha_do_valor_feita = True

            # Cada um recua o próprio topo pelo tanto que falta pra encostar na
            # base comum da linha. O menor desce, o maior fica onde está.
            if chave == "sku":
                elementos.append(Texto(
                    campo="variante.sku", x_mm=margem_x,
                    y_mm=y_da_linha + (linha_valor - linha_normal),
                    largura_mm=metade, tamanho_pt=pt_normal, linhas_max=1,
                    prefixo="SKU: " if rotulo_sku else "", excesso="cortar"))
            else:
                elementos.append(Preco(
                    campo="variante.preco",
                    x_mm=margem_x + (metade if tem_sku else 0),
                    y_mm=y_da_linha + (linha_valor - linha_preco),
                    largura_mm=metade, tamanho_pt=pt_preco,
                    linhas_max=1, alinhamento="dir", negrito=True,
                    simbolo=simbolo, simbolo_depois=simbolo_depois,
                    separador_decimal=separador_decimal,
                    separador_milhar=separador_milhar))

        elif chave == "codigo_barras":
            # Fica sempre grudado na base, e cresce pra cima com o que sobrou.
            # O teto de 42% existe pra barra não virar a etiqueta inteira quando
            # só ela está ligada — mas ele NUNCA encolhe abaixo do mínimo que
            # bipa. Sem esse `max`, a etiqueta de joia saía com barra de 5,0mm:
            # o teto proporcional cortando exatamente a medida que o espaço já
            # tinha sido reservado pra garantir.
            altura_barra = max(BARRA_MINIMA_MM,
                               min(BARRA_MINIMA_MM + max(0.0, orcamento),
                                   altura * 0.42))
            elementos.append(CodigoBarras(
                campo="variante.codigo_barras", x_mm=margem_x,
                y_mm=altura - margem_y - altura_barra - altura_dos_digitos,
                altura_mm=altura_barra, simbologia=simbologia,
                modulo_dots=MODULO_PADRAO_DOTS,
                mostrar_texto=digitos_do_codigo))

    return Template(
        nome=nome or nome_do_formato,
        midia=midia,
        calibracao=Calibracao(desvio_x_mm=desvio_x_mm, desvio_y_mm=desvio_y_mm),
        elementos=elementos)


def nao_couberam(montado: Template, campos) -> list:
    """Quais campos pedidos NÃO entraram NESTE template. A tela avisa antes.

    Sem isto, o lojista liga "fornecedor", não vê diferença nenhuma na prévia e
    conclui que o app está quebrado. Dizer "não coube nesta etiqueta" é uma
    resposta; não mostrar nada não é.

    Recebe o template PRONTO de propósito. A versão anterior remontava um do
    zero com os padrões, e aí o aviso podia discordar do desenho na tela: quem
    escolhesse Code128 numa etiqueta estreita via o código sumir da prévia e
    nenhum aviso dizendo por quê — porque o aviso tinha sido calculado com
    EAN-13. Aviso que discorda da tela é pior que aviso nenhum.
    """
    usados = set()
    for el in montado.elementos:
        for chave, info in CAMPOS.items():
            if el.campo == info["campo"]:
                usados.add(chave)
    return [c for c in (campos or ()) if c in CAMPOS and c not in usados]


def cabem_os_campos(formato: str, campos, **escolhas) -> list:
    """O mesmo, montando o template na hora. Atalho pra teste e pra script."""
    return nao_couberam(montar(formato, campos, **escolhas), campos)
