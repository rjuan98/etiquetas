"""Conversão de medida. O único lugar do projeto que converte milímetro.

Por que milímetro é a unidade do template, e não dot ou ponto:

A mesma etiqueta precisa sair numa Zebra de 203 dpi, numa DYMO de 300 e num PDF
de 72. Milímetro é a única verdade física entre os três — o papel tem 54mm de
largura independente de quem imprime. Cada motor converte na saída.

Começar em dots porque "facilita o ZPL" obriga a reescrever tudo quando entra o
segundo motor. Foi decidido assim de propósito.

E este arquivo existe sozinho por um motivo aprendido na marra: no Hércules, a
mesma conta escrita em treze lugares diferentes divergiu, e a gente passou uma
semana consertando número que discordava de si mesmo. Conversão mora aqui, e só
aqui.
"""

MM_POR_POLEGADA = 25.4

# Densidades que a gente encontra no mundo real.
ZEBRA_203 = 203      # a mais comum em varejo (8 dots/mm)
ZEBRA_300 = 300      # etiqueta pequena, joia, eletrônico
DYMO_300 = 300       # LabelWriter
PDF = 72             # ponto tipográfico, o padrão de PDF


def mm_para_dots(mm: float, dpi: int) -> int:
    """Milímetro para dots da impressora, arredondado.

    O arredondamento é para o inteiro mais próximo porque impressora térmica não
    tem meio dot: pedir 12,5 e receber 12 ou 13 é a diferença entre a etiqueta
    fechar certo ou sobrar uma fresta.
    """
    if dpi <= 0:
        raise ValueError("dpi tem que ser positivo, veio %r" % dpi)
    return round(mm * dpi / MM_POR_POLEGADA)


def mm_para_pontos(mm: float) -> float:
    """Milímetro para ponto tipográfico (PDF). Aqui NÃO arredonda.

    PDF trabalha em ponto flutuante e aceita fração; arredondar aqui jogaria
    fora precisão de graça.
    """
    return mm * PDF / MM_POR_POLEGADA


def dots_para_mm(dots: int, dpi: int) -> float:
    """Volta de dots para milímetro. Serve pro editor mostrar medida de verdade
    quando a pessoa arrasta um elemento na tela."""
    if dpi <= 0:
        raise ValueError("dpi tem que ser positivo, veio %r" % dpi)
    return dots * MM_POR_POLEGADA / dpi


def pontos_para_mm(pontos: float) -> float:
    """Volta de ponto para milímetro."""
    return pontos * MM_POR_POLEGADA / PDF


def dots_por_mm(dpi: int) -> float:
    """Quantos dots cabem num milímetro nesta densidade.

    A 203 dpi dá 7,99 — que é por que todo mundo diz "8 dots por milímetro" e
    por que a conta fecha tão bem nessa densidade.
    """
    return dpi / MM_POR_POLEGADA
