"""Motor ZPL — Zebra e compatíveis.

É o motor mais simples dos três, e o único que dá pra verificar de graça: cola a
saída em labelary.com/viewer.html e vê a etiqueta renderizada, sem impressora.

Duas coisas que o ZPL faz e economizam trabalho:

**Desenha código de barras sozinho.** Manda o número em `^BE` e ele desenha o
EAN-13. Sem gerar imagem, sem biblioteca de código de barras, sem se preocupar
com resolução.

**Posiciona em dot exato.** `^FO50,50` é 50 dots, ponto final. Não tem diálogo de
impressão no meio pra escalar nada — que é exatamente por que o app oficial sai
torto e este não vai sair.

O que ele NÃO faz, e custou uma descoberta: `^LH` não aceita valor negativo. Só
desloca pra direita e pra baixo. Por isso a calibração é aplicada aqui, no
cálculo da coordenada, e não no comando.
"""
from .. import campos, codigos, texto as texto_mod, unidades, valores
from ..modelo import CodigoBarras, Preco, Template, Texto


def _escapar(valor: str) -> str:
    """Neutraliza os caracteres de controle do ZPL dentro do dado.

    `^` e `~` são prefixo de comando. Um produto chamado "Cabo ~ USB" quebraria a
    etiqueta inteira — e produto com caractere estranho no nome é rotina em
    catálogo importado de planilha.
    """
    return (valor or "").replace("^", " ").replace("~", " ")


def _fonte(tamanho_pt: float, dpi: int) -> int:
    """Altura da fonte em dots. O ZPL mede fonte em dot, não em ponto."""
    return max(6, unidades.mm_para_dots(max(0.1, tamanho_pt) * 25.4 / 72, dpi))


def _coord(mm: float, dpi: int) -> int:
    """Coordenada em dots, nunca negativa.

    O `^FO` do ZPL tem a mesma limitação do `^LH`: não aceita valor negativo.
    Uma calibração puxando pra trás mais do que a margem existente gerava
    `^FO-79897`, que a impressora recusa. Grudar na borda é feio; comando
    inválido derruba a etiqueta inteira.
    """
    return max(0, unidades.mm_para_dots(mm, dpi))


def _alinhamento_zpl(alinhamento: str) -> str:
    return {"esq": "L", "dir": "R", "centro": "C"}.get(alinhamento, "L")


def _render_texto(el: Texto, template: Template, dados: dict, dpi: int) -> list[str]:
    # A regra de qual valor sai (campo, formatação de preço, prefixo/sufixo, e o
    # rótulo sumindo junto com o campo vazio) mora em `valores.py`, e os três
    # motores chamam de lá. Antes era escrita aqui e de novo no PDF.
    bruto = valores.do_elemento(el, dados)
    if not bruto:
        return []

    linhas, tamanho_pt = texto_mod.preparar(
        bruto, el.largura_mm, el.tamanho_pt, el.linhas_max, el.excesso)
    if not linhas:
        return []

    x_mm, y_mm = template.com_calibracao(el)
    x = _coord(x_mm, dpi)
    y = _coord(y_mm, dpi)
    altura = _fonte(tamanho_pt, dpi)

    saida = ["^FO%d,%d" % (x, y)]
    if el.largura_mm > 0:
        # ^FB é bloco de texto: largura, linhas, espaçamento, alinhamento, recuo.
        # É ele que quebra a linha e joga o preço pro canto direito.
        saida.append("^FB%d,%d,0,%s,0" % (
            unidades.mm_para_dots(el.largura_mm, dpi),
            el.linhas_max,
            _alinhamento_zpl(el.alinhamento),
        ))
    saida.append("^A0N,%d,%d" % (altura, altura))
    saida.append("^FD%s^FS" % _escapar("\\&".join(linhas)))
    return ["".join(saida)]


def _render_codigo(el: CodigoBarras, template: Template, dados: dict, dpi: int) -> list[str]:
    valor = campos.resolver(el.campo, dados).strip()
    if not valor:
        return []

    # Módulo ou altura zerados geram `^BY0` e `^BY2,3,0`, que são comandos
    # inválidos: a impressora ou recusa a etiqueta ou imprime lixo. Melhor não
    # imprimir código nenhum e deixar a validação avisar antes.
    if el.modulo_dots <= 0 or el.altura_mm <= 0:
        return []

    simbologia = codigos.obter(el.simbologia)
    ok, motivo = codigos.validar(valor, simbologia)
    if not ok:
        # Código inválido não vira barra nenhuma. Imprimir um código que não bipa
        # é pior que não imprimir: o lojista só descobre no caixa, com fila.
        return []

    x_mm, y_mm = template.com_calibracao(el)

    # A zona muda é somada por baixo: a pessoa posiciona onde quer e a norma é
    # respeitada de qualquer jeito. Foi o defeito da primeira etiqueta que a
    # gente renderizou — o dígito inicial do EAN-13 raspando a borda.
    x_mm += codigos.margem_esquerda_mm(simbologia, el.modulo_dots, dpi)

    x = _coord(x_mm, dpi)
    y = _coord(y_mm, dpi)
    altura = unidades.mm_para_dots(el.altura_mm, dpi)
    mostrar = "Y" if el.mostrar_texto else "N"

    if simbologia.bidimensional:
        # ^BQ: orientação, modelo 2 (o atual), e magnificação = tamanho do módulo.
        # O dado do QR leva um prefixo próprio: nível de correção + modo de
        # entrada. "MA" é correção média com modo automático, que é o que serve
        # pra URL e código alfanumérico sem a pessoa escolher nada.
        correcao = (el.correcao_qr or "M").upper()[:1]
        if correcao not in "LMQH":
            correcao = "M"
        return ["^FO%d,%d^BQN,2,%d^FD%sA,%s^FS"
                % (x, y, max(1, el.modulo_dots), correcao, _escapar(valor))]

    saida = ["^BY%d,3,%d" % (el.modulo_dots, altura)]
    if simbologia is codigos.CODE128:
        saida.append("^FO%d,%d%sN,%d,%s,N,N" % (x, y, simbologia.comando_zpl, altura, mostrar))
    else:
        saida.append("^FO%d,%d%sN,%d,%s,N" % (x, y, simbologia.comando_zpl, altura, mostrar))
    saida.append("^FD%s^FS" % valor)
    return ["".join(saida)]


def render(template: Template, dados: dict, dpi: int = unidades.ZEBRA_203) -> str:
    """Template + dados de um produto → ZPL de uma etiqueta.

    O `^CI28` da segunda linha liga UTF-8. Sem ele, acento e € viram lixo — e é
    a linha que todo mundo esquece.
    """
    linhas = [
        "^XA",
        "^CI28",
        "^PW%d" % unidades.mm_para_dots(template.midia.largura_mm, dpi),
        "^LL%d" % unidades.mm_para_dots(template.midia.altura_mm, dpi),
        # ^LH fica em 0,0 sempre: ele não aceita negativo, então a calibração é
        # aplicada coordenada por coordenada em com_calibracao().
        "^LH0,0",
    ]

    for el in template.elementos:
        if isinstance(el, CodigoBarras):
            linhas.extend(_render_codigo(el, template, dados, dpi))
        elif isinstance(el, Texto):
            linhas.extend(_render_texto(el, template, dados, dpi))
        else:
            raise TypeError("elemento que o motor ZPL não conhece: %r" % type(el))

    linhas.append("^XZ")
    return "\n".join(linhas)


def render_lote(template: Template, itens: list, dpi: int = unidades.ZEBRA_203) -> str:
    """Vários produtos de uma vez.

    `itens` é uma lista de (dados, quantidade) — porque imprimir 12 etiquetas do
    mesmo produto é o caso normal de quem recebe carga, e obrigar a pessoa a
    digitar "1" doze vezes é literalmente a reclamação do app oficial.
    """
    saida = []
    for dados, quantidade in itens:
        etiqueta = render(template, dados, dpi)
        saida.extend([etiqueta] * _quantidade(quantidade))
    return "\n".join(saida)


def _quantidade(valor) -> int:
    """Quantidade que sempre vira um inteiro >= 1.

    Vinha de fora (formulário, API, planilha) e podia ser None, texto ou fração.
    Zero ou negativo viraria etiqueta sumindo em silêncio da fila.
    """
    try:
        return max(1, int(float(valor)))
    except (TypeError, ValueError):
        return 1
