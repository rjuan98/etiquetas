"""Gera os PDFs pra conferir com régua.

Uso: python gerar_pdfs.py

Imprima SEMPRE em "tamanho real" / "100%" / "escala: nenhuma".
Se o seu leitor de PDF estiver com "ajustar à página", tudo encolhe uns 3% e a
medição não vale nada — que é exatamente o defeito que este projeto conserta.
"""
import os

from etiquetas.modelo import (Calibracao, CodigoBarras, Midia, Preco, Template,
                              Texto)
from etiquetas.motores import pdf
from exemplo import PRODUTO, etiqueta_2x1

PASTA = "pdfs"

# Avery 5160 / 3x10 em A4 — o formato de folha adesiva mais comum.
AVERY = Midia(
    largura_mm=63.5, altura_mm=25.4, tipo="folha",
    pagina_largura_mm=210, pagina_altura_mm=297,
    colunas=3, linhas=10,
    margem_topo_mm=12.7, margem_esq_mm=7.2,
    espaco_horizontal_mm=2.5, espaco_vertical_mm=0,
)


def folha_avery(calibracao=None):
    base = etiqueta_2x1(calibracao)
    return Template(nome="Avery 3x10", midia=AVERY,
                    calibracao=base.calibracao, elementos=base.elementos)


def salvar(nome, conteudo):
    caminho = os.path.join(PASTA, nome)
    with open(caminho, "wb") as f:
        f.write(conteudo)
    print("  %-34s %6d bytes" % (nome, len(conteudo)))


if __name__ == "__main__":
    os.makedirs(PASTA, exist_ok=True)
    print("Gerando em ./%s/\n" % PASTA)

    # 1. O mais importante pra conferir com régua: A4 com marcas de 5 em 5mm.
    salvar("1_calibracao_A4.pdf", pdf.pagina_de_calibracao(folha_avery()))

    # 2. A folha cheia — dá pra medir se as etiquetas caem na grade certa.
    salvar("2_folha_avery_cheia.pdf", pdf.render(folha_avery(), [(PRODUTO, 30)]))

    # 3. A etiqueta de rolo sozinha, em página do tamanho dela.
    salvar("3_etiqueta_rolo.pdf", pdf.render(etiqueta_2x1(), [(PRODUTO, 1)]))

    # 4. A mesma folha com 2mm de desvio — pra ver a calibração funcionando.
    salvar("4_folha_calibrada_2mm.pdf",
           pdf.render(folha_avery(Calibracao(desvio_x_mm=2, desvio_y_mm=2)),
                      [(PRODUTO, 30)]))

    print("""
O que medir:

  1_calibracao_A4       imprima em TAMANHO REAL e meça as marcas com régua.
                        A marca "50" tem que estar a 50mm exatos da borda
                        esquerda. Se estiver em 48,5, o desvio é 1,5mm.

  2_folha_avery_cheia   a primeira etiqueta deve começar a 7,2mm da esquerda
                        e 12,7mm do topo. Cada etiqueta tem 63,5 x 25,4mm.

  3_etiqueta_rolo       a página inteira deve medir 50,8 x 25,4mm.

  4_folha_calibrada     tudo 2mm mais pra dentro que o arquivo 2. É a mesma
                        etiqueta com a calibração aplicada.
""")
