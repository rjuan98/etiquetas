"""Quebra, corte e encolhimento de texto.

Título de produto de e-commerce é longo e ninguém controla o tamanho: "Canudo de
Vidro Reto 20cm - Kit 4 unidades - Reutilizável Ecológico" tem 62 caracteres e
precisa caber em 47mm.

Duas saídas honestas, e o lojista escolhe qual quer no template:

**cortar** — quebra em N linhas e o que não coube some. Previsível, e o tamanho
da fonte nunca muda entre etiquetas: uma prateleira inteira fica uniforme.

**encolher** — diminui a fonte até caber tudo. Nada some, mas cada etiqueta sai
com um tamanho de letra, e uma prateleira vira colcha de retalho.

O padrão é cortar, porque uniformidade importa mais em prateleira do que ler o
nome completo — quem está olhando já tem o produto na mão.

Nota sobre a medida: fonte escalável de impressora térmica não tem métrica
exposta, então a largura é estimada por proporção. É aproximação de propósito —
o custo de errar é uma linha quebrar um caractere antes, e o custo de acertar
exigiria carregar a métrica de cada fonte de cada impressora.
"""

# Proporção largura/altura de caractere na fonte 0 do ZPL, medida na prática.
# Fonte de impressora térmica é mais estreita que fonte de tela.
PROPORCAO_LARGURA = 0.58


def largura_estimada_mm(texto: str, tamanho_pt: float) -> float:
    """Quanto este texto ocupa, aproximadamente, nesta altura de fonte."""
    altura_mm = tamanho_pt * 25.4 / 72
    return len(texto) * altura_mm * PROPORCAO_LARGURA


def cabe(texto: str, largura_mm: float, tamanho_pt: float) -> bool:
    if largura_mm <= 0:
        return True                       # sem limite de largura
    return largura_estimada_mm(texto, tamanho_pt) <= largura_mm


def quantos_cabem(largura_mm: float, tamanho_pt: float) -> int:
    """Quantos caracteres cabem na largura, direto pela conta.

    Existe porque a versão anterior descobria isso **tirando um caractere por
    vez** até caber. Numa palavra de 40 mil caracteres — que chega fácil, já que
    o conteúdo da etiqueta vem do navegador — isso virava meio segundo de CPU, e
    o custo crescia com o QUADRADO do tamanho: dobrar o texto multiplicava o
    tempo por doze.

    Medido: 10 mil caracteres = 16ms, 20 mil = 39ms, 40 mil = 472ms. Um título
    de 2 MB, que o Flask aceita, travaria um processo inteiro por minutos.

    A medida é linear no número de caracteres (ver `largura_estimada_mm`), então
    o resultado sai de uma divisão. Quem chama ainda confere com `cabe`, porque
    arredondamento de ponto flutuante pode passar por um caractere.
    """
    altura_mm = tamanho_pt * 25.4 / 72
    por_caractere = altura_mm * PROPORCAO_LARGURA
    if por_caractere <= 0:
        return 1
    return max(1, int(largura_mm / por_caractere))


def quebrar(texto: str, largura_mm: float, tamanho_pt: float,
            linhas_max: int = 1) -> list[str]:
    """Quebra em linhas que caibam na largura, respeitando o limite de linhas.

    Quebra por palavra. Palavra sozinha maior que a linha inteira é cortada no
    meio — acontece com código de fornecedor grudado, tipo "REF-ABC123456789".
    """
    texto = (texto or "").strip()
    if not texto:
        return []
    # linhas_max zero ou negativo devolvia lista vazia — o texto sumia da
    # etiqueta em silêncio. Menos de uma linha não existe.
    linhas_max = max(1, int(linhas_max))
    if largura_mm <= 0 or tamanho_pt <= 0:
        return [texto]

    linhas = []
    atual = ""
    for palavra in texto.split():
        tentativa = (atual + " " + palavra).strip()
        if cabe(tentativa, largura_mm, tamanho_pt):
            atual = tentativa
            continue

        if atual:
            linhas.append(atual)
            atual = ""
        if len(linhas) >= linhas_max:
            break

        # A palavra sozinha não cabe: corta no meio.
        while palavra and not cabe(palavra, largura_mm, tamanho_pt):
            # O ponto de corte sai de uma divisão, não de tirar letra por letra.
            # A correção abaixo é só pro arredondamento — roda uma ou duas
            # vezes, nunca milhares. Ver `quantos_cabem`.
            corte = min(len(palavra) - 1, quantos_cabem(largura_mm, tamanho_pt))
            while corte > 1 and not cabe(palavra[:corte], largura_mm, tamanho_pt):
                corte -= 1
            linhas.append(palavra[:corte])
            palavra = palavra[corte:]
            if len(linhas) >= linhas_max:
                palavra = ""
                break
        atual = palavra

    if atual and len(linhas) < linhas_max:
        linhas.append(atual)
    return linhas[:linhas_max]


def encolher_para_caber(texto: str, largura_mm: float, tamanho_pt: float,
                        linhas_max: int = 1, minimo_pt: float = 4.0) -> float:
    """Acha o maior tamanho de fonte em que o texto inteiro ainda cabe.

    Desce de meio em meio ponto. Se nem no mínimo couber, devolve o mínimo e
    quem chamou decide o que fazer — mas devolver fonte ilegível de 2pt seria
    pior que cortar.
    """
    tamanho = tamanho_pt
    while tamanho > minimo_pt:
        linhas = quebrar(texto, largura_mm, tamanho, linhas_max=99)
        if len(linhas) <= linhas_max:
            return tamanho
        tamanho -= 0.5
    return minimo_pt


# Teto de caracteres que entram na conta de quebra.
#
# Uma etiqueta de 10cm com fonte miúda mostra umas 300 letras; 4 mil é folgado
# por qualquer medida. O que vier além disso não caberia de jeito nenhum — é
# cadastro estranho, texto colado por engano, ou alguém empurrando um corpo de
# 2 MB pra ver o servidor suar.
#
# Cortar aqui é barato e não muda nenhuma etiqueta real, porque o `linhas_max`
# já descartaria esse excesso alguns passos adiante.
TETO_DE_CARACTERES = 4000


def preparar(texto: str, largura_mm: float, tamanho_pt: float,
             linhas_max: int = 1, excesso: str = "cortar") -> tuple[list[str], float]:
    """O que os motores chamam. Devolve (linhas, tamanho_final_pt).

    Um lugar só decide como o texto cabe, e os três motores obedecem — senão o
    PDF corta numa palavra e o ZPL corta noutra, e o lojista descobre que as
    etiquetas dele mudam de acordo com a impressora.
    """
    if texto and len(texto) > TETO_DE_CARACTERES:
        texto = texto[:TETO_DE_CARACTERES]
    if excesso == "encolher":
        tamanho_pt = encolher_para_caber(texto, largura_mm, tamanho_pt, linhas_max)
    return quebrar(texto, largura_mm, tamanho_pt, linhas_max), tamanho_pt
