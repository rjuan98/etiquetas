"""O ícone do app, em SVG e em PNG, a partir da MESMA geometria.

    python docs/icone.py

## Por que os dois saem daqui

A loja de apps do Shopify quer PNG de 1200×1200. Mas PNG não se edita: mexer
numa barra significa abrir num programa de desenho e nunca mais bater com o
original.

O caminho óbvio seria manter o SVG à mão e converter. Aí seriam duas fontes da
mesma coisa — o SVG que eu edito e o PNG que alguém gerou uma vez — e elas
divergem no dia em que alguém esquece de reconverter. É a mesma armadilha da
prévia que mente e dos três motores que precisam concordar.

Então a geometria mora em `FORMAS`, e os dois arquivos saem dela.

## As escolhas de desenho, e por quê

**Sem texto.** O Shopify mostra o ícone a ~60px na listagem, e letra nesse
tamanho vira borrão. É também regra deles.

**A etiqueta está reta.** Inclinar daria mais movimento, e contradiria a
promessa central do app — etiqueta que não sai torta.

**Sete barras grossas, não vinte finas.** Vinte barras finas viram um bloco
cinza uniforme no tamanho pequeno, que é justamente onde o ícone precisa
funcionar.

**Marcas de registro nos cantos.** É o que gráfica usa pra conferir se a
impressão caiu no lugar. Diz "impressão precisa" pra quem já viu uma prova, e lê
como enfeite geométrico pra quem não viu.
"""
import io
import os

LADO = 1200
ESCALA = 4          # desenha grande e reduz: é o que dá borda lisa no PIL

FUNDO_TOPO = (43, 58, 103)      # #2B3A67
FUNDO_BASE = (27, 36, 69)       # #1B2445
TINTA = (27, 36, 69)
PAPEL = (255, 255, 255)
MARCA = (124, 138, 184)         # #7C8AB8

# Cada forma: (tipo, geometria, cor, opacidade). Um lugar só.
FORMAS = [
    # marcas de registro — quatro cantos, cruz aberta
    ("linha", (150, 262, 236, 262), MARCA, 0.55),
    ("linha", (193, 219, 193, 305), MARCA, 0.55),
    ("linha", (964, 262, 1050, 262), MARCA, 0.55),
    ("linha", (1007, 219, 1007, 305), MARCA, 0.55),
    ("linha", (150, 938, 236, 938), MARCA, 0.55),
    ("linha", (193, 895, 193, 981), MARCA, 0.55),
    ("linha", (964, 938, 1050, 938), MARCA, 0.55),
    ("linha", (1007, 895, 1007, 981), MARCA, 0.55),

    # a etiqueta
    ("caixa", (290, 358, 910, 842, 34), PAPEL, 1.0),
    # o furo do cordão: é o que faz o retângulo virar "etiqueta", não "papel"
    ("circulo", (338, 406, 398, 466), TINTA, 1.0),

    # as barras, larguras variadas pra ler como código de barras de verdade
    ("caixa", (446, 424, 476, 652, 6), TINTA, 1.0),
    ("caixa", (496, 424, 512, 652, 5), TINTA, 1.0),
    ("caixa", (532, 424, 574, 652, 6), TINTA, 1.0),
    ("caixa", (594, 424, 610, 652, 5), TINTA, 1.0),
    ("caixa", (630, 424, 660, 652, 6), TINTA, 1.0),
    ("caixa", (680, 424, 726, 652, 6), TINTA, 1.0),
    ("caixa", (746, 424, 762, 652, 5), TINTA, 1.0),
    ("caixa", (782, 424, 812, 652, 6), TINTA, 1.0),

    # a linha do preço: o segundo motivo pelo qual a etiqueta existe
    ("caixa", (446, 706, 676, 740, 17), FUNDO_TOPO, 0.35),
    ("caixa", (700, 706, 812, 740, 17), FUNDO_TOPO, 1.0),
]

LARGURA_DA_MARCA = 14


def _hex(cor):
    return "#%02X%02X%02X" % cor


def svg() -> str:
    partes = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" '
              'width="%d" height="%d" role="img" '
              'aria-label="Barcode label aligned by registration marks">'
              % (LADO, LADO, LADO, LADO)]
    partes.append(
        '<defs><linearGradient id="fundo" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s"/>'
        '</linearGradient></defs>' % (_hex(FUNDO_TOPO), _hex(FUNDO_BASE)))
    # Sangra até a borda: cada plataforma recorta o canto do seu jeito.
    partes.append('<rect width="%d" height="%d" fill="url(#fundo)"/>' % (LADO, LADO))

    for tipo, g, cor, op in FORMAS:
        alfa = ' opacity="%s"' % op if op < 1 else ""
        if tipo == "linha":
            partes.append('<path d="M%g %g L%g %g" stroke="%s" stroke-width="%d" '
                          'stroke-linecap="square"%s/>'
                          % (g[0], g[1], g[2], g[3], _hex(cor),
                             LARGURA_DA_MARCA, alfa))
        elif tipo == "caixa":
            partes.append('<rect x="%g" y="%g" width="%g" height="%g" rx="%g" '
                          'fill="%s"%s/>'
                          % (g[0], g[1], g[2] - g[0], g[3] - g[1], g[4],
                             _hex(cor), alfa))
        elif tipo == "circulo":
            partes.append('<circle cx="%g" cy="%g" r="%g" fill="%s"%s/>'
                          % ((g[0] + g[2]) / 2, (g[1] + g[3]) / 2,
                             (g[2] - g[0]) / 2, _hex(cor), alfa))
    partes.append("</svg>")
    return "\n".join(partes) + "\n"


def png(caminho: str, lado: int = LADO):
    from PIL import Image, ImageDraw

    n = lado * ESCALA
    k = n / LADO

    # Gradiente do fundo, linha a linha.
    base = Image.new("RGB", (n, n))
    desenho = ImageDraw.Draw(base)
    for y in range(n):
        p = y / (n - 1)
        desenho.line(
            [(0, y), (n, y)],
            fill=tuple(int(a + (b - a) * p)
                       for a, b in zip(FUNDO_TOPO, FUNDO_BASE)))

    # As formas vão numa camada com transparência, pra opacidade valer.
    camada = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(camada)
    for tipo, g, cor, op in FORMAS:
        rgba = cor + (int(round(op * 255)),)
        if tipo == "linha":
            d.line([(g[0] * k, g[1] * k), (g[2] * k, g[3] * k)],
                   fill=rgba, width=int(LARGURA_DA_MARCA * k))
        elif tipo == "caixa":
            d.rounded_rectangle([g[0] * k, g[1] * k, g[2] * k, g[3] * k],
                                radius=g[4] * k, fill=rgba)
        elif tipo == "circulo":
            d.ellipse([g[0] * k, g[1] * k, g[2] * k, g[3] * k], fill=rgba)

    base.paste(camada, (0, 0), camada)
    # Reduzir no fim é o que dá borda lisa: o PIL não suaviza ao desenhar.
    base.resize((lado, lado), Image.LANCZOS).save(caminho, "PNG")


if __name__ == "__main__":
    aqui = os.path.dirname(os.path.abspath(__file__))
    io.open(os.path.join(aqui, "icone.svg"), "w", encoding="utf-8").write(svg())
    png(os.path.join(aqui, "icone.png"))
    # 60px é o tamanho da listagem, onde a maioria vê o ícone pela primeira vez.
    png(os.path.join(aqui, "icone-60.png"), 60)
    print("icone.svg, icone.png (1200) e icone-60.png gerados")
