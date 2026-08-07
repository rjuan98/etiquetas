"""A forma do template. É o ativo do projeto — todo o resto é tradutor.

Um template descreve uma etiqueta em milímetro, sem saber quem vai imprimir.
O mesmo objeto vira ZPL na Zebra, XML na DYMO e PDF em folha.

Duas decisões que parecem detalhe e não são:

**Versão.** O campo `esquema` existe para a promessa do produto: "seu template
não muda sozinho, nunca". O Shopify mudou a fonte dos lojistas numa atualização
de julho de 2026 e as etiquetas de todo mundo pararam de combinar. Aqui, mudança
de comportamento exige versão nova — o template antigo continua renderizando
igual pra sempre.

**Calibração no modelo, não no motor.** A primeira tentativa foi usar `^LH` do
ZPL, e o linter avisou: `^LH` não aceita valor negativo, só desloca pra direita
e pra baixo. Desvio de impressora vai pros dois lados, então `^LH` é inútil aqui.
Aplicando no modelo, os três motores calibram igual, com o mesmo número, testado
uma vez.
"""
from dataclasses import dataclass, field


@dataclass
class Calibracao:
    """O desvio que o lojista mediu com régua, em milímetro.

    Positivo empurra pra direita e pra baixo; negativo puxa pra esquerda e pra
    cima. Os dois sentidos importam, e é por isso que isto não pode virar `^LH`.
    """
    desvio_x_mm: float = 0.0
    desvio_y_mm: float = 0.0


@dataclass
class Midia:
    """O papel. Rolo (uma etiqueta por vez) ou folha (uma grade delas).

    As medidas têm padrão de propósito: template meio salvo no banco, ou JSON
    truncado, precisa pelo menos ABRIR pra pessoa consertar. Sem padrão,
    qualquer registro incompleto derrubava a tela inteira em vez de mostrar um
    aviso.
    """
    largura_mm: float = 50.8           # 2 polegadas, a etiqueta de varejo comum
    altura_mm: float = 25.4
    tipo: str = "rolo"                 # "rolo" ou "folha"

    # Só para folha: a grade. Uma folha Avery é isto e mais nada.
    #
    # A folha tem DUAS medidas que não podem se confundir: o papel (A4, Carta) e
    # a etiqueta dentro dele. `largura_mm` e `altura_mm` acima são sempre da
    # ETIQUETA — inclusive na folha. O papel é o par abaixo.
    pagina_largura_mm: float = 210.0     # A4 de pé
    pagina_altura_mm: float = 297.0
    colunas: int = 1
    linhas: int = 1
    margem_topo_mm: float = 0.0
    margem_esq_mm: float = 0.0
    espaco_horizontal_mm: float = 0.0
    espaco_vertical_mm: float = 0.0


@dataclass
class Elemento:
    """Base de tudo que se põe numa etiqueta. Posição sempre em milímetro."""
    x_mm: float
    y_mm: float
    campo: str = ""                    # "produto.titulo", "variante.sku"...


@dataclass
class Texto(Elemento):
    largura_mm: float = 0.0            # 0 = sem quebra, escreve numa linha só
    tamanho_pt: float = 8.0
    linhas_max: int = 1
    alinhamento: str = "esq"           # "esq", "dir", "centro"
    excesso: str = "cortar"            # "cortar" ou "encolher"
    negrito: bool = False

    # Texto fixo antes e depois do valor: "SKU: " + CAN-VD-20 + " un".
    # Com `campo` vazio, o elemento vira texto puramente fixo — que é como se
    # põe nome da loja, "Indústria Brasileira" ou qualquer rótulo constante.
    prefixo: str = ""
    sufixo: str = ""


@dataclass
class Preco(Texto):
    """Preço é texto com regra de formatação própria.

    Existe separado porque o símbolo, a posição dele e os separadores mudam por
    país — e uma loja francesa não conseguia pôr o € à direita no app oficial.
    Deixar isso configurável é literalmente uma das reclamações.
    """
    simbolo: str = "R$"
    simbolo_depois: bool = False
    separador_decimal: str = ","
    separador_milhar: str = "."


@dataclass
class CodigoBarras(Elemento):
    simbologia: str = "CODE128"
    largura_mm: float = 30.0
    altura_mm: float = 10.0
    modulo_dots: int = 2               # largura da barra mais fina
    mostrar_texto: bool = True

    # Só para QR. "M" recupera ~15% de dano e é o equilíbrio certo pra etiqueta:
    # "L" (7%) não sobrevive a um dedo sujo, "H" (30%) engorda o código sem
    # necessidade num papel que não vai apanhar.
    correcao_qr: str = "M"

    def quadrado(self) -> bool:
        """QR é quadrado: a altura manda, e a largura acompanha."""
        from . import codigos
        try:
            return codigos.obter(self.simbologia).bidimensional
        except ValueError:
            return False


@dataclass
class Template:
    nome: str
    midia: Midia
    elementos: list = field(default_factory=list)
    calibracao: Calibracao = field(default_factory=Calibracao)
    esquema: int = 1

    def com_calibracao(self, elemento: Elemento) -> tuple[float, float]:
        """A posição final de um elemento, já com o desvio aplicado.

        Todo motor chama isto e nenhum motor recalcula por conta própria. É o
        "uma regra, um lugar" que faltou no Hércules.
        """
        return (elemento.x_mm + self.calibracao.desvio_x_mm,
                elemento.y_mm + self.calibracao.desvio_y_mm)
