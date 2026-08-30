"""Motor SVG — a prévia na tela. Uma etiqueta, do jeito que vai sair.

## Por que a prévia é um motor, e não desenho em JavaScript

O caminho óbvio seria desenhar a etiqueta no navegador com canvas ou HTML. É mais
rápido de fazer e responde instantâneo a cada clique.

E seria **redesenhar a mesma regra numa segunda linguagem**. Aí a quebra de linha
do JavaScript discorda da quebra do Python em uma palavra, e a prévia mostra uma
etiqueta que a impressora não vai imprimir. Este app existe justamente porque o
app oficial faz a etiqueta mudar sozinha — construir uma prévia que mente seria
recriar o defeito com outro nome.

Então a prévia sai daqui, do servidor, chamando `texto.preparar`, `valores`,
`codigos` e `unidades` — os mesmos que o ZPL e o PDF chamam. Custa uma ida ao
servidor por mudança. Vale.

O código de barras vem do **mesmo desenho do reportlab** que o motor PDF usa,
convertido pra SVG. Não é um gerador parecido: é o mesmo objeto.

## Diferença de eixo em relação ao PDF

SVG tem origem no canto superior esquerdo e Y crescendo pra baixo — igual ao
nosso modelo, igual ao ZPL. É o PDF que é o esquisito dos três. Por isso aqui
**não tem conversão de Y nenhuma**, e é de propósito: se um dia aparecer um
`altura - y` neste arquivo, é bug.

## A unidade do desenho é o milímetro

O `viewBox` é em milímetro, então toda coordenada no SVG é literalmente o número
que está no modelo. Sem escala intermediária pra conferir quando algo sair torto.
Quem escala é o CSS, na tela.
"""
import re

from reportlab.graphics import renderSVG
from reportlab.graphics.barcode import createBarcodeDrawing

from .. import campos, codigos, texto as texto_mod, unidades, valores
from ..modelo import CodigoBarras, Template, Texto
from .pdf import NOME_REPORTLAB

# Fonte de tela que existe em Windows, Mac e Linux sem precisar carregar arquivo.
# Não é a Helvetica do PDF nem a fonte da Zebra — nenhuma prévia de tela é
# idêntica ao papel, e prometer isso seria mentira. O que importa é que a
# QUEBRA e o POSICIONAMENTO sejam os mesmos, e esses vêm do `texto.preparar`.
FONTE = "Helvetica, Arial, sans-serif"

_PROLOGO = re.compile(r"^.*?(?=<svg)", re.DOTALL)


def _escapar(valor: str) -> str:
    """XML não perdoa `&`, `<` e `>` soltos.

    Produto chamado "Camiseta P&B" quebraria o SVG inteiro — e nome com `&` é
    rotina em catálogo. O ZPL tem o problema equivalente com `^` e `~`.
    """
    return ((valor or "").replace("&", "&amp;")
            .replace("<", "&lt;").replace(">", "&gt;"))


def _mm(valor: float) -> str:
    """Número curto. SVG com 14 casas decimais é ilegível e pesa à toa."""
    return ("%.3f" % float(valor)).rstrip("0").rstrip(".") or "0"


def _texto_svg(el: Texto, template: Template, dados: dict) -> list:
    bruto = valores.do_elemento(el, dados)
    if not bruto:
        return []

    # A MESMA chamada que o PDF e o ZPL fazem. É esta linha que garante que a
    # prévia quebre o texto onde a impressora vai quebrar.
    linhas, tamanho_pt = texto_mod.preparar(
        bruto, el.largura_mm, el.tamanho_pt, el.linhas_max, el.excesso)
    if not linhas:
        return []

    x_mm, y_mm = template.com_calibracao(el)
    tamanho_mm = tamanho_pt * 25.4 / 72
    altura_linha_mm = tamanho_mm * 1.15      # mesmo respiro do motor PDF

    if el.largura_mm > 0 and el.alinhamento == "dir":
        ancora, x_texto = "end", x_mm + el.largura_mm
    elif el.largura_mm > 0 and el.alinhamento == "centro":
        ancora, x_texto = "middle", x_mm + el.largura_mm / 2
    else:
        ancora, x_texto = "start", x_mm

    saida = []
    for i, linha in enumerate(linhas):
        # (i+1) porque o Y do SVG é a LINHA DE BASE do texto, não o topo — mesma
        # convenção do PDF. Sem isso a primeira linha nasce cortada pela borda.
        saida.append(
            '<text x="%s" y="%s" font-family="%s" font-size="%s" '
            'font-weight="%s" text-anchor="%s" fill="#000">%s</text>'
            % (_mm(x_texto), _mm(y_mm + (i + 1) * altura_linha_mm), FONTE,
               _mm(tamanho_mm), "bold" if el.negrito else "normal",
               ancora, _escapar(linha)))
    return saida


def _codigo_svg(el: CodigoBarras, template: Template, dados: dict) -> list:
    valor = campos.resolver(el.campo, dados).strip()
    if not valor:
        return []
    if el.modulo_dots <= 0 or el.altura_mm <= 0:
        return []

    simbologia = codigos.obter(el.simbologia)
    ok, _motivo = codigos.validar(valor, simbologia)
    if not ok:
        # Mesma regra dos outros motores: código que não bipa não é desenhado.
        # E na prévia isso é informação — o lojista VÊ que o código sumiu, e é
        # assim que ele descobre o cadastro errado antes de gastar etiqueta.
        return []

    # Idem pro que vaza pela borda: some da prévia, então o lojista descobre
    # ANTES de imprimir, em vez de descobrir no papel.
    if not codigos.cabe_na_largura(simbologia, valor, el.modulo_dots,
                                   unidades.ZEBRA_203, el.x_mm,
                                   template.midia.largura_mm, el.altura_mm):
        return []

    modulo_mm = unidades.dots_para_mm(el.modulo_dots, unidades.ZEBRA_203)
    x_mm, y_mm = template.com_calibracao(el)
    x_mm += codigos.margem_esquerda_mm(simbologia, el.modulo_dots, unidades.ZEBRA_203)

    if simbologia.bidimensional:
        # O lado sai de `codigos`, não do `altura_mm` cru: é lá que mora a
        # quantização que faz o ZPL, o PDF e a prévia desenharem o MESMO
        # tamanho. Ver `lado_do_qr_mm`.
        lado_mm, _mag = codigos.lado_do_qr_mm(
            valor, el.altura_mm, unidades.ZEBRA_203, el.correcao_qr)
        lado = unidades.mm_para_pontos(lado_mm)
        desenho = createBarcodeDrawing(NOME_REPORTLAB[simbologia.nome],
                                       value=valor, barWidth=lado, barHeight=lado)
    else:
        desenho = createBarcodeDrawing(
            NOME_REPORTLAB[simbologia.nome], value=valor,
            barWidth=unidades.mm_para_pontos(modulo_mm),
            barHeight=unidades.mm_para_pontos(el.altura_mm),
            humanReadable=el.mostrar_texto, quiet=False)

    # O desenho do reportlab sai em pontos; o nosso mundo é milímetro.
    largura_mm = desenho.width * 25.4 / 72
    altura_desenho_mm = desenho.height * 25.4 / 72

    interno = _PROLOGO.sub("", renderSVG.drawToString(desenho), count=1)
    # O `<svg>` interno traz width/height próprios em ponto. Trocar pelos nossos
    # em milímetro é o que faz o código sair do tamanho FÍSICO certo — e tamanho
    # de código de barras não é estética: fora da medida, o leitor não pega.
    interno = re.sub(r'^<svg[^>]*?width="[^"]*"', '<svg', interno, count=1)
    interno = re.sub(r'^(<svg[^>]*?)\s+height="[^"]*"', r"\1", interno, count=1)
    interno = interno.replace(
        "<svg", '<svg x="%s" y="%s" width="%s" height="%s"'
        % (_mm(x_mm), _mm(y_mm), _mm(largura_mm), _mm(altura_desenho_mm)), 1)
    return [interno]


def render(template: Template, dados: dict, moldura: bool = True) -> str:
    """Template + dados de UM produto → SVG da etiqueta.

    `moldura` desenha a borda da etiqueta. É só prévia: mostra onde o papel
    termina, pra pessoa ver que o texto está encostando na borda antes de
    imprimir duzentas.
    """
    m = template.midia
    if m.largura_mm <= 0 or m.altura_mm <= 0:
        raise ValueError(
            "a etiqueta ficou com %gx%gmm. Confira a medida."
            % (m.largura_mm, m.altura_mm))

    corpo = []
    for el in template.elementos:
        if isinstance(el, CodigoBarras):
            corpo.extend(_codigo_svg(el, template, dados))
        elif isinstance(el, Texto):
            corpo.extend(_texto_svg(el, template, dados))
        else:
            raise TypeError("elemento que o motor SVG não conhece: %r" % type(el))

    if moldura:
        corpo.insert(0, '<rect x="0" y="0" width="%s" height="%s" fill="#fff" '
                        'stroke="#c9cccf" stroke-width="0.2"/>'
                        % (_mm(m.largura_mm), _mm(m.altura_mm)))
    else:
        corpo.insert(0, '<rect x="0" y="0" width="%s" height="%s" fill="#fff"/>'
                        % (_mm(m.largura_mm), _mm(m.altura_mm)))

    return (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'xmlns:xlink="http://www.w3.org/1999/xlink" '
        'viewBox="0 0 %s %s" width="100%%" '
        'preserveAspectRatio="xMidYMid meet" role="img" '
        'aria-label="Prévia da etiqueta">%s</svg>'
        % (_mm(m.largura_mm), _mm(m.altura_mm), "".join(corpo)))
