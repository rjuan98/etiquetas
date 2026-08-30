"""Regras de código de barras: simbologia, dígito verificador e zona muda.

A zona muda é o motivo deste arquivo existir separado.

Todo código de barras exige uma faixa de papel EM BRANCO antes e depois das
barras, medida em módulos (a largura da barra mais fina). Sem ela, o leitor não
acha onde o código começa e a etiqueta simplesmente não bipa — às vezes. O
"às vezes" é o pior: o lojista jura que o app está bom porque funcionou nos dez
primeiros testes dele.

Isso apareceu na primeira etiqueta que a gente renderizou: o EAN-13 imprime o
primeiro dígito FORA das barras, à esquerda, e a 2mm da borda ele ficava
raspando o papel. Aqui vira regra, não sorte.
"""
import functools

from dataclasses import dataclass


@dataclass(frozen=True)
class Simbologia:
    """As regras de uma simbologia. Frozen porque isto é norma, não configuração."""
    nome: str
    comando_zpl: str          # ^BE é EAN-13, ^BC é Code128, ^BQ é QR
    zona_muda_esq: int        # em módulos
    zona_muda_dir: int
    digitos_min: int          # 0 = aceita texto livre
    digitos_max: int
    tem_verificador: bool
    # QR é bidimensional: quadrado, sem linha de número embaixo, e aceita texto
    # de qualquer tamanho. Os motores desenham de um jeito diferente, então o
    # sinalizador mora aqui e não espalhado por `if simbologia.nome == "QRCODE"`.
    bidimensional: bool = False
    # Quantos caracteres cabem antes de o QR ficar denso demais pra ler numa
    # etiqueta pequena. Não é limite do padrão (que vai a milhares) — é limite
    # prático: URL longa vira um borrão que nenhum celular lê a 2cm.
    limite_pratico: int = 0
    # O `^Bx` do ZPL aceita um parâmetro a mais em algumas simbologias: o
    # "calcular dígito verificador". Quem tem, recebe um ",N" extra — a gente já
    # manda o código completo e não quer que a impressora acrescente outro.
    verificador_no_zpl: bool = False
    # Razão entre a barra larga e a barra fina. Só existe nas simbologias que
    # TÊM barra larga (o ITF-14 tem; o EAN-13 não, todas as barras dele são
    # múltiplos do módulo).
    #
    # Isto é obrigatório e custou uma medição: o reportlab usa 2,2 por padrão e o
    # `^BY` do ZPL usa 3,0. Sem fixar, o MESMO ITF-14 sairia 21% mais largo na
    # Zebra do que no PDF e na prévia — o defeito que este projeto existe pra
    # corrigir, e o mesmo que já tinha aparecido no QR.
    razao_larga: float = 0.0


EAN13 = Simbologia("EAN13", "^BE", 11, 7, 12, 13, True)
UPCA = Simbologia("UPCA", "^BU", 9, 9, 11, 12, True)
CODE128 = Simbologia("CODE128", "^BC", 10, 10, 0, 0, False,
                     verificador_no_zpl=True)
# ITF-14 é o código da CAIXA de atacado — o que vai na embalagem coletiva, não
# na peça. Sempre 14 dígitos (é um GTIN-14), e a zona muda dele é de 10 módulos,
# maior que a do EAN-13.
#
# Não desenhamos as "barras de suporte" (as tarjas grossas em cima e embaixo que
# a norma pede em papelão ondulado). Em etiqueta adesiva, que é o nosso caso,
# ninguém imprime — mas está dito na ficha pra não parecer omissão.
ITF14 = Simbologia("ITF14", "^B2", 10, 10, 14, 14, True,
                   verificador_no_zpl=True, razao_larga=3.0)
# QR exige zona muda de 4 módulos em TODOS os lados, não só nas laterais.
QRCODE = Simbologia("QRCODE", "^BQ", 4, 4, 0, 0, False,
                    bidimensional=True, limite_pratico=300)

POR_NOME = {s.nome: s for s in (EAN13, UPCA, CODE128, QRCODE, ITF14)}


# Como as pessoas escrevem, e o nome canônico. "QR" é o que todo mundo digita.
APELIDOS = {"QR": "QRCODE", "QRCODE": "QRCODE", "EAN": "EAN13", "UPC": "UPCA",
            "CODE128": "CODE128", "C128": "CODE128",
            "ITF14": "ITF14", "ITF": "ITF14", "GTIN14": "ITF14",
            "I2OF5": "ITF14"}


def obter(nome: str) -> Simbologia:
    nome = (nome or "").upper().replace("-", "").replace(" ", "")
    nome = APELIDOS.get(nome, nome)
    if nome not in POR_NOME:
        raise ValueError(
            "simbologia %r não existe. Disponíveis: %s"
            % (nome, ", ".join(sorted(POR_NOME)))
        )
    return POR_NOME[nome]


def digito_verificador_gs1(digitos: str) -> str:
    """O dígito verificador do GS1, pra qualquer comprimento.

    O mesmo algoritmo serve pro EAN-13 (12 dígitos), UPC-A (11) e ITF-14 (13):
    contando **da direita pra esquerda**, os pesos alternam 3 e 1, e o
    verificador é o que falta pra fechar na dezena.

    A versão anterior contava da ESQUERDA e só funcionava com 12 dígitos — o que
    dá o mesmo resultado pro EAN-13, por sorte do comprimento par, e o resultado
    ERRADO pro UPC-A e pro ITF-14.
    """
    if not digitos or not digitos.isdigit():
        raise ValueError("preciso de dígitos, veio %r" % digitos)
    soma = 0
    for i, char in enumerate(reversed(digitos)):
        soma += int(char) * (3 if i % 2 == 0 else 1)
    return str((10 - soma % 10) % 10)


def digito_verificador_ean(doze_digitos: str) -> str:
    """O 13º dígito do EAN-13, pelo algoritmo do padrão.

    Posições ímpares valem 1x, pares valem 3x, e o verificador é o que falta pra
    fechar na dezena. A impressora calcula sozinha quando recebe 12 dígitos, mas
    a gente precisa da conta pra VALIDAR quando o lojista manda 13 — código com
    verificador errado imprime bonito e não bipa nunca.
    """
    if len(doze_digitos) != 12 or not doze_digitos.isdigit():
        raise ValueError("preciso de exatamente 12 dígitos, veio %r" % doze_digitos)
    return digito_verificador_gs1(doze_digitos)


def validar(valor: str, simbologia: Simbologia) -> tuple[bool, str]:
    """Confere se o valor pode virar este código de barras.

    Devolve (ok, motivo). O motivo é escrito pra aparecer na tela do lojista, não
    pro log: quem lê é quem vai consertar o cadastro do produto.
    """
    valor = (valor or "").strip()
    if not valor:
        return False, "está vazio"

    if simbologia.limite_pratico and len(valor) > simbologia.limite_pratico:
        return False, ("são %d caracteres. Acima de %d o QR fica denso demais pra "
                       "ler numa etiqueta pequena — use um link encurtado"
                       % (len(valor), simbologia.limite_pratico))

    if simbologia.digitos_min == 0:
        return True, ""          # Code128 e QR aceitam texto

    if not valor.isdigit():
        return False, "o %s só aceita número, e veio %r" % (simbologia.nome, valor)

    if not (simbologia.digitos_min <= len(valor) <= simbologia.digitos_max):
        if simbologia.digitos_min == simbologia.digitos_max:
            quantos = "%d dígitos" % simbologia.digitos_max
        else:
            quantos = "%d ou %d dígitos" % (simbologia.digitos_min,
                                            simbologia.digitos_max)
        return False, "o %s precisa de %s, e veio com %d" % (
            simbologia.nome, quantos, len(valor))

    # Se veio completo, confere o verificador. Se veio sem, a impressora calcula.
    #
    # Isto valia SÓ pro EAN-13, e era um buraco: UPC-A com verificador errado
    # passava direto e ia pro papel. Código errado imprime bonito, bipa, e traz
    # o produto errado no caixa — que é a pior falha possível aqui, porque
    # ninguém desconfia dela. É a queixa de uma estrela que um concorrente
    # levou. O algoritmo é o mesmo do GS1 pras três simbologias numéricas.
    if simbologia.tem_verificador and len(valor) == simbologia.digitos_max:
        esperado = digito_verificador_gs1(valor[:-1])
        if valor[-1] != esperado:
            return False, ("o dígito verificador está errado: termina em %s e "
                           "deveria terminar em %s" % (valor[-1], esperado))
    return True, ""


def margem_esquerda_mm(simbologia: Simbologia, modulo_dots: int, dpi: int) -> float:
    """Quanto de papel em branco o código precisa à esquerda, em milímetro.

    É esta função que impede a etiqueta que não bipa. O gerador soma isto ao x
    pedido — a pessoa posiciona onde quer e a norma é respeitada por baixo.
    """
    from . import unidades
    return unidades.dots_para_mm(simbologia.zona_muda_esq * modulo_dots, dpi)


def margem_direita_mm(simbologia: Simbologia, modulo_dots: int, dpi: int) -> float:
    from . import unidades
    return unidades.dots_para_mm(simbologia.zona_muda_dir * modulo_dots, dpi)


# Quantos módulos cada símbolo ocupa. É estrutura da norma, não escolha nossa.
#
#   EAN-13 e UPC-A têm largura FIXA: 95 módulos, sempre, não importa o número.
#   Code 128 é variável: 11 por caractere, mais 35 de início, verificador e fim.
MODULOS_FIXOS = {"EAN13": 95, "UPCA": 95,
                 # Medido no reportlab com razão 3,0: 135 módulos. Com a razão
                 # 2,2 do padrão dele daria 112 — e o ZPL desenharia 135. Ver
                 # `Simbologia.razao_larga`.
                 "ITF14": 135}
MODULOS_POR_CARACTERE = 11
MODULOS_DE_ENQUADRAMENTO = 35


@functools.lru_cache(maxsize=512)
def modulos_do_qr(valor: str, correcao: str = "M") -> int:
    """Quantos módulos tem o lado da matriz do QR, pro dado que ele vai levar.

    Depende do tamanho do dado e do nível de correção: uma URL de 47 caracteres
    dá 33×33; uma de 120 dá 57×57. É por isso que QR não tem largura fixa como o
    EAN-13 tem.

    **Custa caro**: 10ms medidos, porque o reportlab só entrega a contagem depois
    de montar a matriz inteira. Um EAN-13 custa 0,01ms. Por isso o cache — cada
    etiqueta pergunta duas vezes (uma pra ver se cabe na largura, outra pra
    desenhar), e sem ele um lote de 300 etiquetas gastava 6,4 segundos de CPU.

    Tentei atalhar chamando o codificador direto, sem montar o desenho. Não
    serve: ele força modo byte e devolve 69 módulos onde o caminho certo dá 57
    pra dado alfanumérico. Superestimar a largura faria o app recusar código que
    cabia.
    """
    from reportlab.graphics.barcode import qr

    nivel = (correcao or "M").upper()[:1]
    if nivel not in "LMQH":
        nivel = "M"
    widget = qr.QrCodeWidget(valor or " ", barLevel=nivel)
    widget.draw()
    return len(widget.qr.modules)


def lado_do_qr_mm(valor: str, altura_mm: float, dpi: int,
                  correcao: str = "M") -> tuple:
    """O lado FÍSICO do QR e a magnificação que produz esse lado.

    Existe por causa de uma divergência medida entre os motores: o mesmo modelo,
    com o mesmo dado, saía **18,0mm no PDF e no SVG e 16,5mm no ZPL**.

    A causa é que o ZPL não aceita "desenhe com 18mm". O `^BQ` recebe uma
    MAGNIFICAÇÃO inteira, e o lado é `módulos × magnificação` — então o tamanho
    físico depende do tamanho do dado. O motor usava `modulo_dots` como
    magnificação, que não tem relação nenhuma com o tamanho pedido: uma URL
    longa (matriz 57) na magnificação 4 dá 28,5mm num campo de 18mm, e o QR sai
    andando pra fora da etiqueta.

    A saída é escolher a magnificação que chega mais perto da altura pedida, e
    fazer os TRÊS motores desenharem esse lado. O QR fica quantizado — 16,5mm em
    vez de 18mm — mas os três concordam, que é a promessa do projeto. Etiqueta
    que muda de tamanho conforme a impressora é o defeito que a gente corrige.
    """
    from . import unidades

    modulos = modulos_do_qr(valor, correcao)
    alvo_dots = unidades.mm_para_dots(max(0.0, altura_mm), dpi)
    magnificacao = max(1, min(10, round(alvo_dots / modulos)))
    return unidades.dots_para_mm(modulos * magnificacao, dpi), magnificacao


def largura_necessaria_mm(simbologia: Simbologia, valor: str, modulo_dots: int,
                          dpi: int, altura_mm: float = 0.0) -> float:
    """Quanto de largura o código precisa, com zona muda, pra caber de verdade.

    Existe porque um código que não cabe **não encolhe: ele vaza pela borda**, e
    o lojista só descobre no papel. É o mesmo tipo de defeito que este app existe
    pra corrigir, então deixá-lo passar aqui seria contradição.

    Apareceu ao acrescentar a etiqueta de 1x1 polegada: um EAN-13 legível precisa
    de ~28mm e o papel tem 25,4mm. Não é limitação nossa — é a norma contra a
    régua. Nenhum formato do catálogo esbarrava nisso, mas medida livre deixaria
    qualquer largura ser digitada.
    """
    from . import unidades

    if simbologia.bidimensional:
        # QR é quadrado: a largura é o lado — e o lado é o que os motores VÃO
        # desenhar, não o que o modelo pediu. Ver `lado_do_qr_mm`.
        lado, mag = lado_do_qr_mm(valor, altura_mm, dpi)
        return lado + (margem_esquerda_mm(simbologia, mag, dpi)
                       + margem_direita_mm(simbologia, mag, dpi))

    modulos = MODULOS_FIXOS.get(simbologia.nome)
    if modulos is None:
        modulos = (MODULOS_POR_CARACTERE * len(valor or "")
                   + MODULOS_DE_ENQUADRAMENTO)

    barras = unidades.dots_para_mm(modulos * max(1, modulo_dots), dpi)
    return (barras
            + margem_esquerda_mm(simbologia, modulo_dots, dpi)
            + margem_direita_mm(simbologia, modulo_dots, dpi))


# O código mais curto que cada simbologia produz na prática. Serve pra responder
# uma pergunta diferente da do `cabe_na_largura`: não "este código cabe", mas
# "ALGUM código desta simbologia caberia neste papel?".
#
# EAN-13 e UPC-A têm largura fixa, então aqui o valor é exato. Code128 varia com
# o dado, e 6 caracteres é o SKU curto de verdade — mais curto que isso ninguém
# usa, e usar 1 caractere daria uma resposta otimista e inútil.
VALOR_MAIS_CURTO = {
    "EAN13": "7891234567895",
    "UPCA": "012345678905",
    "CODE128": "ABC123",
    "QRCODE": "ABC123",
    "ITF14": "10789123456785",
}


def largura_minima_mm(simbologia: Simbologia, modulo_dots: int, dpi: int,
                      altura_mm: float = 0.0) -> float:
    """O menor espaço horizontal em que esta simbologia ainda produz código.

    É o que o montador de layout usa pra decidir se o código de barras entra:
    se nem o mais curto cabe na largura do papel, o campo não entra e o lojista
    lê o motivo na tela — em vez de ligar o código, não ver nada, e concluir que
    o app está quebrado.
    """
    return largura_necessaria_mm(
        simbologia, VALOR_MAIS_CURTO.get(simbologia.nome, "ABC123"),
        modulo_dots, dpi, altura_mm)


def cabe_na_largura(simbologia: Simbologia, valor: str, modulo_dots: int, dpi: int,
                    x_mm: float, largura_da_etiqueta_mm: float,
                    altura_mm: float = 0.0) -> bool:
    """O código cabe no papel a partir de onde ele foi posicionado?

    Os três motores chamam isto logo depois do `validar`, e pelo mesmo motivo:
    código que vaza pela borda não bipa, exatamente como código com verificador
    errado não bipa. A diferença é que este o lojista **só descobre no papel**.

    Etiqueta sem medida (largura zero ou negativa) devolve True: quem valida
    medida é o `esquema`, e não cabe a esta função ter opinião sobre isso.
    """
    if largura_da_etiqueta_mm <= 0:
        return True
    precisa = largura_necessaria_mm(simbologia, valor, modulo_dots, dpi, altura_mm)
    return x_mm + precisa <= largura_da_etiqueta_mm + 0.01
