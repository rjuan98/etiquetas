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


EAN13 = Simbologia("EAN13", "^BE", 11, 7, 12, 13, True)
UPCA = Simbologia("UPCA", "^BU", 9, 9, 11, 12, True)
CODE128 = Simbologia("CODE128", "^BC", 10, 10, 0, 0, False)
# QR exige zona muda de 4 módulos em TODOS os lados, não só nas laterais.
QRCODE = Simbologia("QRCODE", "^BQ", 4, 4, 0, 0, False,
                    bidimensional=True, limite_pratico=300)

POR_NOME = {s.nome: s for s in (EAN13, UPCA, CODE128, QRCODE)}


# Como as pessoas escrevem, e o nome canônico. "QR" é o que todo mundo digita.
APELIDOS = {"QR": "QRCODE", "QRCODE": "QRCODE", "EAN": "EAN13", "UPC": "UPCA",
            "CODE128": "CODE128", "C128": "CODE128"}


def obter(nome: str) -> Simbologia:
    nome = (nome or "").upper().replace("-", "").replace(" ", "")
    nome = APELIDOS.get(nome, nome)
    if nome not in POR_NOME:
        raise ValueError(
            "simbologia %r não existe. Disponíveis: %s"
            % (nome, ", ".join(sorted(POR_NOME)))
        )
    return POR_NOME[nome]


def digito_verificador_ean(doze_digitos: str) -> str:
    """O 13º dígito do EAN-13, pelo algoritmo do padrão.

    Posições ímpares valem 1x, pares valem 3x, e o verificador é o que falta pra
    fechar na dezena. A impressora calcula sozinha quando recebe 12 dígitos, mas
    a gente precisa da conta pra VALIDAR quando o lojista manda 13 — código com
    verificador errado imprime bonito e não bipa nunca.
    """
    if len(doze_digitos) != 12 or not doze_digitos.isdigit():
        raise ValueError("preciso de exatamente 12 dígitos, veio %r" % doze_digitos)
    soma = 0
    for i, char in enumerate(doze_digitos):
        soma += int(char) * (1 if i % 2 == 0 else 3)
    return str((10 - soma % 10) % 10)


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
        return False, "o %s precisa de %d ou %d dígitos, e veio com %d" % (
            simbologia.nome, simbologia.digitos_min, simbologia.digitos_max, len(valor))

    # Se veio completo, confere o verificador. Se veio sem, a impressora calcula.
    if simbologia.tem_verificador and len(valor) == simbologia.digitos_max:
        if simbologia is EAN13:
            esperado = digito_verificador_ean(valor[:12])
            if valor[12] != esperado:
                return False, ("o dígito verificador está errado: termina em %s e "
                               "deveria terminar em %s" % (valor[12], esperado))
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
