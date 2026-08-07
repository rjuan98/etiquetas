"""Gera uma etiqueta de exemplo pra colar no Labelary.

Uso:  python exemplo.py            → etiqueta normal
      python exemplo.py calibrada  → com desvio de 1mm à direita, 0,5mm acima

Cole a saída em labelary.com/viewer.html, com 2 x 1 polegada e 8 dpmm (203 dpi).
"""
import sys

from etiquetas.modelo import (Calibracao, CodigoBarras, Midia, Preco, Template,
                              Texto)
from etiquetas.motores import zpl

PRODUTO = {
    "produto": {"titulo": "Canudo de Vidro Reto 20cm - Kit 4 unidades"},
    "variante": {
        "sku": "CAN-VD-20",
        "codigo_barras": "789123456789",
        "preco": "24.90",
    },
}


def etiqueta_2x1(calibracao=None):
    """Etiqueta 2x1 polegada de varejo: título, SKU, preço e EAN-13."""
    return Template(
        nome="2x1 varejo",
        midia=Midia(largura_mm=50.8, altura_mm=25.4),
        calibracao=calibracao or Calibracao(),
        elementos=[
            Texto(x_mm=2, y_mm=1, campo="produto.titulo",
                  largura_mm=46.75, tamanho_pt=7.8, linhas_max=2),
            Texto(x_mm=2, y_mm=7.75, campo="variante.sku", prefixo="SKU: ",
                  tamanho_pt=6.4),
            Preco(x_mm=2, y_mm=7.25, campo="variante.preco",
                  largura_mm=46.75, tamanho_pt=10, alinhamento="dir"),
            CodigoBarras(x_mm=2, y_mm=11.5, campo="variante.codigo_barras",
                         simbologia="EAN13", altura_mm=7.5, modulo_dots=2),
        ],
    )


if __name__ == "__main__":
    calibrada = len(sys.argv) > 1 and sys.argv[1].startswith("cal")
    cal = Calibracao(desvio_x_mm=1.0, desvio_y_mm=-0.5) if calibrada else None
    print(zpl.render(etiqueta_2x1(cal), PRODUTO))
