"""Motor PDF — folha adesiva (Avery e parecidas) e rolo sem impressora térmica.

É o motor mais trabalhoso dos três, e o motivo é o mesmo que faz o app oficial
sair torto: **o diálogo de impressão do navegador escala o documento**. Quem
manda imprimir com "ajustar à página" ligado vê tudo encolher 3% e a etiqueta
nunca mais bate com o papel.

Duas defesas contra isso:

**A página sai no tamanho físico exato.** Uma folha A4 tem 210×297mm no PDF, não
"mais ou menos A4". Aí basta o lojista imprimir em **tamanho real / 100%**, e a
calibração cuida do resto.

**Página de calibração.** `pagina_de_calibracao()` desenha uma régua impressa.
A pessoa imprime, mede com régua de verdade, e digita o desvio. É a mesma
calibração do ZPL, com o mesmo número, aplicada no mesmo lugar do modelo.

## O detalhe que mais gera bug: o eixo Y

PDF tem origem no canto INFERIOR esquerdo e o Y cresce pra cima. O nosso modelo
(e o ZPL, e a intuição de qualquer pessoa) tem origem no canto SUPERIOR esquerdo
e o Y cresce pra baixo.

Toda conversão passa por `_y_pdf()`. Se algum dia uma etiqueta sair espelhada na
vertical, é aqui que se olha.
"""
import io
from dataclasses import replace

from reportlab.graphics.barcode import createBarcodeDrawing
from reportlab.lib.colors import black
from reportlab.pdfgen import canvas

from .. import campos, codigos, texto as texto_mod, unidades, valores
from ..modelo import CodigoBarras, Preco, Template, Texto

# Como cada simbologia nossa se chama no reportlab. A tradução mora aqui e em
# nenhum outro lugar — acrescentar simbologia é acrescentar uma linha.
NOME_REPORTLAB = {
    "EAN13": "EAN13",
    "UPCA": "UPCA",
    "CODE128": "Code128",
    "QRCODE": "QR",
    "ITF14": "I2of5",
}

def argumentos_reportlab(simbologia) -> dict:
    """O que o reportlab precisa além do valor, por simbologia.

    Existe pra ser chamado pelos DOIS motores que usam reportlab (o PDF e a
    prévia). Escrever em cada um seria garantir que um dia divergissem — e
    divergir aqui significa a prévia mostrar um código de uma largura e o papel
    sair com outra.

    O `ratio` é o caso que obrigou a criar isto: o reportlab usa 2,2 por padrão
    e o `^BY` do ZPL usa 3,0. Sem igualar, o mesmo ITF-14 sairia 21% mais largo
    na Zebra. Medido, não suposto.

    O `checksum=0` é porque a gente já valida e já manda o código COMPLETO. Com
    o padrão (1) o reportlab acrescentaria um 15º dígito.
    """
    extras = {}
    if simbologia.razao_larga:
        extras["ratio"] = simbologia.razao_larga
        extras["checksum"] = 0
    return extras


# Helvetica vem embutida no PDF e cobre acento latino sem precisar carregar
# arquivo de fonte. Fonte customizada é assunto de depois, e vai exigir embutir
# o .ttf no PDF pra etiqueta abrir igual em qualquer computador.
FONTE = "Helvetica"
FONTE_NEGRITO = "Helvetica-Bold"


def _pt(mm: float) -> float:
    return unidades.mm_para_pontos(mm)


def _quantidade(valor) -> int:
    """Igual à do motor ZPL: quantidade que vem de fora sempre vira >= 1."""
    try:
        return max(1, int(float(valor)))
    except (TypeError, ValueError):
        return 1


def _y_pdf(y_mm_topo: float, altura_total_mm: float) -> float:
    """Y do nosso modelo (de cima pra baixo) para Y do PDF (de baixo pra cima)."""
    return _pt(altura_total_mm - y_mm_topo)


def _desenhar_texto(c, el: Texto, dados: dict, ox_mm: float, oy_mm: float,
                    altura_pagina_mm: float):
    # Ver `valores.py`: esta regra era escrita aqui e outra vez no motor ZPL.
    bruto = valores.do_elemento(el, dados)
    if not bruto:
        return

    linhas, tamanho_pt = texto_mod.preparar(
        bruto, el.largura_mm, el.tamanho_pt, el.linhas_max, el.excesso)
    if not linhas:
        return

    c.setFont(FONTE_NEGRITO if el.negrito else FONTE, tamanho_pt)
    c.setFillColor(black)

    # Espaçamento entre linhas de 1,15 — o mesmo respiro que o olho espera em
    # texto corrido. Mais apertado que isso, duas linhas viram um borrão.
    altura_linha_mm = tamanho_pt * 25.4 / 72 * 1.15

    for i, linha in enumerate(linhas):
        y_mm = el.y_mm + oy_mm + (i + 1) * altura_linha_mm
        y = _y_pdf(y_mm, altura_pagina_mm)

        if el.largura_mm > 0 and el.alinhamento == "dir":
            c.drawRightString(_pt(el.x_mm + ox_mm + el.largura_mm), y, linha)
        elif el.largura_mm > 0 and el.alinhamento == "centro":
            c.drawCentredString(_pt(el.x_mm + ox_mm + el.largura_mm / 2), y, linha)
        else:
            c.drawString(_pt(el.x_mm + ox_mm), y, linha)


def _desenhar_codigo(c, el: CodigoBarras, dados: dict, ox_mm: float, oy_mm: float,
                     altura_pagina_mm: float, largura_etiqueta_mm: float = 0.0):
    valor = campos.resolver(el.campo, dados).strip()
    if not valor:
        return

    # Mesma guarda do ZPL: módulo ou altura zerados não viram código nenhum.
    if el.modulo_dots <= 0 or el.altura_mm <= 0:
        return

    simbologia = codigos.obter(el.simbologia)
    ok, _motivo = codigos.validar(valor, simbologia)
    if not ok:
        # Mesma regra do ZPL: código que não bipa é pior que código nenhum,
        # porque o lojista só descobre no caixa, com fila.
        return

    # E o que vaza pela borda também não bipa.
    if not codigos.cabe_na_largura(simbologia, valor, el.modulo_dots,
                                   unidades.ZEBRA_203, el.x_mm,
                                   largura_etiqueta_mm, el.altura_mm):
        return

    # A largura do módulo é definida em dots de impressora térmica no template.
    # Convertida pra milímetro, ela vale igual aqui — é assim que a mesma
    # etiqueta sai do mesmo tamanho físico nos dois motores.
    modulo_mm = unidades.dots_para_mm(el.modulo_dots, unidades.ZEBRA_203)

    x_mm = el.x_mm + ox_mm + codigos.margem_esquerda_mm(
        simbologia, el.modulo_dots, unidades.ZEBRA_203)
    y_base_mm = el.y_mm + oy_mm + el.altura_mm

    # `quiet=False` desliga a zona muda do reportlab de propósito: quem cuida
    # dela é o codigos.py, com a mesma regra que o motor ZPL usa. Deixar os dois
    # aplicarem margem daria uma margem dupla no PDF e simples no ZPL — a mesma
    # etiqueta saindo diferente conforme a impressora.
    if simbologia.bidimensional:
        # QR é quadrado: no reportlab, barWidth e barHeight são o LADO do
        # desenho inteiro, não o tamanho do módulo. A altura manda e a largura
        # acompanha, senão o código sai esticado e nenhum leitor pega.
        # Mesmo lado dos outros dois motores — ver `codigos.lado_do_qr_mm`.
        lado_mm, _mag = codigos.lado_do_qr_mm(
            valor, el.altura_mm, unidades.ZEBRA_203, el.correcao_qr)
        lado = _pt(lado_mm)
        desenho = createBarcodeDrawing(
            NOME_REPORTLAB[simbologia.nome],
            value=valor, barWidth=lado, barHeight=lado,
        )
    else:
        desenho = createBarcodeDrawing(
            NOME_REPORTLAB[simbologia.nome],
            value=valor,
            barWidth=_pt(modulo_mm),
            barHeight=_pt(el.altura_mm),
            humanReadable=el.mostrar_texto,
            quiet=False,
            **argumentos_reportlab(simbologia),
        )
    desenho.drawOn(c, _pt(x_mm), _y_pdf(y_base_mm, altura_pagina_mm))


def _desenhar_etiqueta(c, template: Template, dados: dict,
                       ox_mm: float, oy_mm: float, altura_pagina_mm: float):
    """Uma etiqueta, na posição (ox, oy) da página. Calibração já somada.

    A cópia é feita com `dataclasses.replace`, que devolve um objeto da MESMA
    CLASSE com x e y trocados. A primeira versão usava uma classe-embrulho que
    repassava atributos — e ela quebrou o `isinstance(el, Preco)` em silêncio: o
    preço saía "24.90" no PDF e "R$ 24,90" no ZPL, a mesma etiqueta diferente
    conforme a impressora.

    Foi o teste de consistência entre motores que pegou. Vale lembrar disso na
    próxima vez que embrulhar objeto parecer uma boa ideia.
    """
    for el in template.elementos:
        x_cal, y_cal = template.com_calibracao(el)
        posicionado = replace(el, x_mm=x_cal, y_mm=y_cal)
        if isinstance(el, CodigoBarras):
            _desenhar_codigo(c, posicionado, dados, ox_mm, oy_mm, altura_pagina_mm,
                             template.midia.largura_mm)
        elif isinstance(el, Texto):
            _desenhar_texto(c, posicionado, dados, ox_mm, oy_mm, altura_pagina_mm)
        else:
            raise TypeError("elemento que o motor PDF não conhece: %r" % type(el))


def _posicoes_na_folha(m) -> list:
    """Onde cada etiqueta começa na folha, em milímetro, de cima pra baixo.

    Grade zerada ou negativa derrubava com divisão por zero mais adiante. Uma
    folha sempre tem pelo menos uma posição — e a validação avisa do resto.
    """
    posicoes = []
    for linha in range(max(1, int(m.linhas))):
        for coluna in range(max(1, int(m.colunas))):
            x = m.margem_esq_mm + coluna * (m.largura_mm + m.espaco_horizontal_mm)
            y = m.margem_topo_mm + linha * (m.altura_mm + m.espaco_vertical_mm)
            posicoes.append((x, y))
    return posicoes


def render(template: Template, itens: list) -> bytes:
    """Template + [(dados, quantidade)] → PDF.

    Rolo: uma etiqueta por página, e a página tem o tamanho da etiqueta.
    Folha: a grade preenchida da esquerda pra direita, de cima pra baixo, abrindo
    página nova quando acaba.
    """
    m = template.midia
    buffer = io.BytesIO()

    # Expande a quantidade numa fila achatada. "12 do mesmo produto" é o caso
    # normal de quem recebe carga — e obrigar a digitar 1 doze vezes é
    # literalmente a reclamação do app oficial.
    fila = []
    for dados, quantidade in itens:
        fila.extend([dados] * _quantidade(quantidade))

    if m.tipo == "folha":
        largura_pag, altura_pag = m.pagina_largura_mm, m.pagina_altura_mm
        posicoes = _posicoes_na_folha(m)
    else:
        largura_pag, altura_pag = m.largura_mm, m.altura_mm
        posicoes = [(0.0, 0.0)]

    # Página de medida zero ou negativa gerava um PDF que abre e não mostra
    # nada. Erro claro é melhor que arquivo vazio que o lojista vai jurar que
    # imprimiu.
    if largura_pag <= 0 or altura_pag <= 0:
        raise ValueError(
            "a página ficou com %gx%gmm. Confira a medida da etiqueta ou do papel."
            % (largura_pag, altura_pag))

    c = canvas.Canvas(buffer, pagesize=(_pt(largura_pag), _pt(altura_pag)))

    for i, dados in enumerate(fila):
        posicao = i % len(posicoes)
        if posicao == 0 and i > 0:
            c.showPage()
        ox_mm, oy_mm = posicoes[posicao]
        _desenhar_etiqueta(c, template, dados, ox_mm, oy_mm, altura_pag)

    c.showPage()
    c.save()
    return buffer.getvalue()


def pagina_de_calibracao(template: Template) -> bytes:
    """Uma régua impressa, pra descobrir o desvio da impressora.

    O lojista imprime esta página em tamanho real, mede com régua de verdade onde
    as marcas caíram, e digita a diferença. É a mesma calibração do ZPL, com o
    mesmo número, guardada no mesmo lugar do modelo.

    Sem isso, "minha etiqueta sai torta" não tem conversa possível — o lojista
    não sabe dizer QUANTO está torto, e a gente não tem o que corrigir.
    """
    m = template.midia
    largura = m.pagina_largura_mm if m.tipo == "folha" else m.largura_mm
    altura = m.pagina_altura_mm if m.tipo == "folha" else m.altura_mm

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(_pt(largura), _pt(altura)))
    c.setLineWidth(0.4)

    # Marcas de 5 em 5mm nas duas bordas, numeradas de 10 em 10.
    c.setFont(FONTE, 5)
    passo = 5
    for mm in range(0, int(largura) + 1, passo):
        tamanho = 4 if mm % 10 else 7
        c.line(_pt(mm), _y_pdf(0, altura), _pt(mm), _y_pdf(tamanho, altura))
        if mm % 10 == 0:
            c.drawString(_pt(mm + 0.5), _y_pdf(tamanho + 3.5, altura), str(mm))
    for mm in range(0, int(altura) + 1, passo):
        tamanho = 4 if mm % 10 else 7
        c.line(_pt(0), _y_pdf(mm, altura), _pt(tamanho), _y_pdf(mm, altura))
        if mm % 10 == 0:
            c.drawString(_pt(tamanho + 1), _y_pdf(mm + 1, altura), str(mm))

    # Moldura de onde a primeira etiqueta DEVERIA cair.
    ox, oy = (m.margem_esq_mm, m.margem_topo_mm) if m.tipo == "folha" else (0, 0)
    c.setDash(3, 3)
    c.rect(_pt(ox), _y_pdf(oy + m.altura_mm, altura),
           _pt(m.largura_mm), _pt(m.altura_mm))
    c.setDash()

    c.setFont(FONTE, 8)
    c.drawString(_pt(ox + 2), _y_pdf(oy + m.altura_mm / 2, altura),
                 "Imprima em tamanho real (100%) e meça esta moldura.")
    c.setFont(FONTE, 6.5)
    c.drawString(_pt(ox + 2), _y_pdf(oy + m.altura_mm / 2 + 4, altura),
                 "Se ela saiu deslocada, informe o desvio em milimetros nas configuracoes.")

    c.showPage()
    c.save()
    return buffer.getvalue()
