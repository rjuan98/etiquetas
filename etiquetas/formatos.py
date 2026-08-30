"""Catálogo de papel de etiqueta pronto.

Sem isto, montar uma folha Avery exige o lojista digitar **oito números** —
largura, altura, colunas, linhas, duas margens e dois espaçamentos. Ele não sabe
nenhum deles de cabeça, vai medir errado com régua, e desiste na primeira tela.

Com isto, ele escolhe "Avery 5160" numa lista e a primeira etiqueta sai em dois
minutos.

Isso é onboarding, e onboarding é onde app morre. Vale mais que funcionalidade.

## AVISO IMPORTANTE, e ele é honesto

As medidas abaixo vêm da especificação publicada de cada fabricante, mas **não
foram conferidas contra papel de verdade** — não temos as folhas em mãos.

Papel de etiqueta varia entre lote e entre fabricante genérico. É exatamente por
isso que a **calibração existe**: a pessoa imprime a página de teste, mede, e
corrige o resto. O catálogo é o ponto de partida, não a palavra final.

Quando alguém confirmar uma medida com papel na mão, marque com `conferido=True`.
"""
from dataclasses import dataclass

from .modelo import Midia

A4 = (210.0, 297.0)
CARTA = (215.9, 279.4)          # US Letter


@dataclass(frozen=True)
class Formato:
    codigo: str
    nome: str
    midia: Midia
    fabricante: str = ""
    conferido: bool = False     # alguém já mediu com papel na mão?

    def novo(self) -> Midia:
        """Uma cópia, porque Midia é mutável e o catálogo não pode ser editado.

        Sem a cópia, um lojista mudando a margem no editor mudaria o formato
        para todos os outros — o tipo de bug que só aparece quando há dois
        usuários e ninguém entende.
        """
        return Midia(**vars(self.midia))


def _folha(larg, alt, pagina, colunas, linhas, topo, esq, gap_h=0.0, gap_v=0.0):
    return Midia(largura_mm=larg, altura_mm=alt, tipo="folha",
                 pagina_largura_mm=pagina[0], pagina_altura_mm=pagina[1],
                 colunas=colunas, linhas=linhas,
                 margem_topo_mm=topo, margem_esq_mm=esq,
                 espaco_horizontal_mm=gap_h, espaco_vertical_mm=gap_v)


def _rolo(larg, alt):
    return Midia(largura_mm=larg, altura_mm=alt, tipo="rolo")


CATALOGO = [
    # ---- Rolo, impressora térmica ----
    Formato("zebra_2x1", "2 x 1 pol — varejo", _rolo(50.8, 25.4), "Zebra e genéricas"),
    Formato("zebra_3x2", "3 x 2 pol", _rolo(76.2, 50.8), "Zebra e genéricas"),
    Formato("zebra_4x6", "4 x 6 pol — envio", _rolo(101.6, 152.4), "Zebra e genéricas"),
    Formato("dymo_30336", "30336 — multiuso", _rolo(54.0, 25.4), "DYMO"),
    Formato("dymo_30252", "30252 — endereço", _rolo(88.9, 28.6), "DYMO"),
    Formato("dymo_30299", "30299 — joia, 2 abas", _rolo(56.0, 12.0), "DYMO"),

    # ---- Folha adesiva ----
    Formato("avery_5160", "5160 — 30 por folha",
            _folha(66.7, 25.4, CARTA, 3, 10, 12.7, 4.8, 3.2, 0.0), "Avery (Carta)"),
    Formato("avery_5163", "5163 — 10 por folha",
            _folha(101.6, 50.8, CARTA, 2, 5, 12.7, 4.8, 3.2, 0.0), "Avery (Carta)"),
    Formato("avery_l7160", "L7160 — 21 por folha",
            _folha(63.5, 38.1, A4, 3, 7, 15.1, 7.2, 2.5, 0.0), "Avery (A4)"),
    Formato("avery_l7163", "L7163 — 14 por folha",
            _folha(99.1, 38.1, A4, 2, 7, 15.1, 5.0, 2.5, 0.0), "Avery (A4)"),
    Formato("pimaco_6180", "6180 — 20 por folha",
            _folha(101.6, 25.4, CARTA, 2, 10, 12.7, 4.8, 3.2, 0.0), "Pimaco (Brasil)"),
    # Pedidos por lojistas que reclamaram do app oficial, com nome e loja.
    # Ver docs/primeiros-lojistas.md — demanda com nome vale mais que palpite.
    Formato("avery_5167", "5167 — 80 por folha",
            _folha(44.45, 12.7, CARTA, 4, 20, 12.7, 7.62, 7.62, 0.0), "Avery (Carta)"),
    Formato("rolo_1x1", "1 x 1 pol",
            Midia(largura_mm=25.4, altura_mm=25.4), "Rolo"),
    # Faltam os formatos A4 da Pimaco, que é o papel mais vendido no Brasil.
    #
    # Eu tinha posto um aqui, deduzido por analogia com a versão Carta — e a
    # `conferir_grade()` reprovou na hora: duas colunas de 101,6mm não cabem nos
    # 210mm da A4, sobrava 1,2mm. Dava pra "consertar" apertando as margens até
    # a conta fechar, mas seria número inventado que o lojista confiaria e
    # imprimiria torto.
    #
    # Fica em branco de propósito, até alguém medir uma folha de verdade.
]

POR_CODIGO = {f.codigo: f for f in CATALOGO}


# Medida livre: o lojista digita largura e altura, e o resto do motor trata
# igual a um rolo. Pedido por nome — THATS-RALLY e Rill reclamaram publicamente
# de não poder digitar a medida da etiqueta que já compraram.
LIVRE = "livre"

# Os limites são de bom senso, não de norma. Abaixo de 8mm não cabe nem uma
# linha de texto legível; acima de 300mm não existe impressora de etiqueta, e
# número absurdo aqui vira etiqueta gigante que trava o navegador na prévia.
MENOR_MEDIDA_MM = 8.0
MAIOR_MEDIDA_MM = 300.0


def midia_livre(largura_mm: float, altura_mm: float) -> Midia:
    """Uma mídia com a medida que o lojista digitou, dentro do bom senso.

    Não valida em silêncio: medida fora dos limites levanta erro, porque a
    alternativa é o lojista digitar 2000 e receber uma etiqueta que nenhuma
    impressora aceita, sem entender por quê.
    """
    for nome, valor in (("largura", largura_mm), ("altura", altura_mm)):
        try:
            valor = float(valor)
        except (TypeError, ValueError):
            raise ValueError("%s tem que ser um número" % nome)
        if not (MENOR_MEDIDA_MM <= valor <= MAIOR_MEDIDA_MM):
            raise ValueError(
                "%s de %.1fmm está fora do que dá pra imprimir (%.0f a %.0fmm)"
                % (nome, valor, MENOR_MEDIDA_MM, MAIOR_MEDIDA_MM))
    return Midia(largura_mm=float(largura_mm), altura_mm=float(altura_mm),
                 tipo="rolo")


def obter(codigo: str) -> Formato:
    if codigo not in POR_CODIGO:
        raise ValueError(
            "formato %r não existe. Disponíveis: %s"
            % (codigo, ", ".join(sorted(POR_CODIGO)))
        )
    return POR_CODIGO[codigo]


def midia(codigo: str) -> Midia:
    """O atalho que o editor usa: código → mídia pronta pra montar template."""
    return obter(codigo).novo()


def por_tipo(tipo: str) -> list:
    """Separado por rolo e folha, que é como a pessoa escolhe.

    A primeira pergunta do onboarding não é "qual etiqueta?" — é "você tem
    impressora de etiqueta ou vai usar folha adesiva na impressora comum?".
    """
    return [f for f in CATALOGO if f.midia.tipo == tipo]


def cabem_por_folha(codigo: str) -> int:
    """Quantas etiquetas saem numa folha. Rolo devolve 1."""
    m = obter(codigo).midia
    return m.colunas * m.linhas if m.tipo == "folha" else 1


def conferir_grade(codigo: str) -> list:
    """A grade cabe mesmo no papel que ela diz caber?

    Catálogo digitado à mão erra, e o erro é invisível: as etiquetas saem
    empilhando pra fora da folha e a última fileira imprime no nada. Esta função
    existe pra a bateria de testes conferir o catálogo inteiro sozinha.
    """
    m = obter(codigo).midia
    if m.tipo != "folha":
        return []

    problemas = []
    largura_usada = (m.margem_esq_mm + m.colunas * m.largura_mm
                     + (m.colunas - 1) * m.espaco_horizontal_mm)
    altura_usada = (m.margem_topo_mm + m.linhas * m.altura_mm
                    + (m.linhas - 1) * m.espaco_vertical_mm)

    if largura_usada > m.pagina_largura_mm + 0.5:
        problemas.append(
            "%s: as %d colunas ocupam %.1fmm numa página de %.1fmm"
            % (codigo, m.colunas, largura_usada, m.pagina_largura_mm))
    if altura_usada > m.pagina_altura_mm + 0.5:
        problemas.append(
            "%s: as %d linhas ocupam %.1fmm numa página de %.1fmm"
            % (codigo, m.linhas, altura_usada, m.pagina_altura_mm))
    return problemas
