"""Gera o número que vai no campo *código de barras* do produto.

Isto é o oposto do `skus.py`, e a diferença decide o desenho inteiro:

**SKU não tem dono. Código de barras tem.**

Cada faixa de numeração pertence a alguém. Gerar um número de uma faixa que não
é do lojista é pôr na prateleira dele um código que pertence a outra empresa — e
isso não aparece na hora. Aparece quando o produto chega ao caixa de outro
varejista e bipa como outra coisa.

Por isso aqui não existe "gerar código" no singular. Existem **três situações**,
e o lojista precisa saber em qual ele está:

| modo | o que é | onde vale |
|---|---|---|
| `gs1`     | GTIN-13 do prefixo de empresa DELE     | no mundo todo |
| `interno` | EAN-13 na faixa 2, circulação restrita | só na loja dele |
| `sku`     | Code 128 com o SKU que já existe       | só na loja dele |

Ver `docs/gerador-de-codigo.md` para a medição que levou a estes três.

## O que este módulo NÃO faz, de propósito

**Não confere se o prefixo é mesmo do lojista.** Não há como — a GS1 não expõe
isso. O que dá pra fazer é dizer na tela, antes, que o campo é pro prefixo
*dele*; `AVISO_DO_MODO` existe pra garantir que seja dito.

**Não escreve em lugar nenhum.** Função pura: itens entram, tabela sai. É ela
que deixa a prévia existir antes de o app pedir qualquer permissão de escrita.

**Não sobrescreve código que já existe.** Um código em uso pode estar impresso
em caixa fechada, e pode ser comprado. Trocar é estrago sem volta.
"""
from . import campos, codigos

# Os três casos. A chave viaja na requisição; o valor é o rótulo do que o número
# É — e esse rótulo vai pra tela junto de cada linha, porque código interno
# apresentado como GTIN é mentira com consequência comercial.
MODOS = {
    "gs1":     "GTIN-13",
    "interno": "código interno (EAN-13, faixa 2)",
    "sku":     "Code 128 a partir do SKU",
}

# Cada modo PRECISA de uma frase na tela dizendo onde aquele código vale —
# não enterrada numa ajuda. É a regra 5 do desenho, e ela existe porque código
# interno apresentado como GTIN é mentira com consequência comercial.
#
# O que mora aqui é a CHAVE, e não o texto: o app é bilíngue, e mandar
# português pra tela em inglês seria falhar justamente na frase mais delicada.
# O texto mora em `web/textos.py`, e um teste confere que todo modo daqui tem
# a sua frase lá, nos dois idiomas — é o teste que impede a divergência.
AVISO_DO_MODO = {
    "gs1": "codigo_aviso_gs1",
    "interno": "codigo_aviso_interno",
    "sku": "codigo_aviso_sku",
}

# A faixa que a norma GS1 reserva ao uso interno de loja. É a única que dá pra
# usar sem ter comprado prefixo de ninguém.
FAIXA_INTERNA = "2"

TAMANHO_DO_GTIN = 13

# Um prefixo de empresa precisa deixar espaço pro item: são 12 dígitos antes do
# verificador, menos o prefixo. Com 12 não sobra nenhum.
PREFIXO_MINIMO = 4
PREFIXO_MAXIMO = TAMANHO_DO_GTIN - 2


def _casas(faixa: str) -> int:
    """Quantos dígitos sobram pro número do item depois da faixa."""
    return TAMANHO_DO_GTIN - 1 - len(faixa)


def conferir_prefixo(prefixo: str) -> list:
    """Os problemas do prefixo, em português, ou lista vazia.

    Devolve lista em vez de levantar porque a tela mostra todos de uma vez — e
    porque o lojista digitando prefixo errado é o caso comum, não o raro.
    """
    prefixo = (prefixo or "").strip()
    if not prefixo:
        return ["Digite o prefixo de empresa que a GS1 deu à sua empresa."]
    if not prefixo.isdigit():
        return ["O prefixo tem só números. Veio %r." % prefixo]
    if len(prefixo) < PREFIXO_MINIMO:
        return ["Prefixo de empresa tem pelo menos %d dígitos. Este tem %d."
                % (PREFIXO_MINIMO, len(prefixo))]
    if len(prefixo) > PREFIXO_MAXIMO:
        return ["Com %d dígitos não sobra espaço para numerar o produto. "
                "O prefixo vai até %d dígitos." % (len(prefixo), PREFIXO_MAXIMO)]
    return []


def capacidade(prefixo: str) -> int:
    """Quantos produtos cabem nesta faixa.

    Prefixo longo é prefixo de empresa pequena: com 11 dígitos sobram 10
    números. Vale dizer isso ANTES de gravar 300 produtos e parar no décimo.
    """
    faixa = (prefixo or "").strip()
    if faixa != FAIXA_INTERNA and conferir_prefixo(faixa):
        return 0
    return 10 ** _casas(faixa) - 1


def _montar(faixa: str, sequencia: int) -> str:
    """Faixa + número do item + verificador = 13 dígitos.

    O verificador vem de `codigos.digito_verificador_gs1`, que conta da direita
    pra esquerda — a versão que contava da esquerda acertava o EAN-13 por sorte
    do comprimento e errava o UPC-A.
    """
    limite = capacidade(faixa)
    if sequencia < 1 or sequencia > limite:
        raise ValueError("a faixa %s comporta de 1 a %d, veio %d"
                         % (faixa, limite, sequencia))
    corpo = faixa + str(sequencia).zfill(_casas(faixa))
    return corpo + codigos.digito_verificador_gs1(corpo)


def montar_gtin(prefixo: str, sequencia: int) -> str:
    """Um GTIN-13 do prefixo de empresa do lojista. Vale no mundo todo."""
    problemas = conferir_prefixo(prefixo)
    if problemas:
        raise ValueError("; ".join(problemas))
    return _montar(prefixo.strip(), sequencia)


def montar_interno(sequencia: int) -> str:
    """Um EAN-13 da faixa de circulação restrita.

    Bipa em qualquer leitor; vale na loja de quem gerou, e em lugar nenhum além
    dela.
    """
    return _montar(FAIXA_INTERNA, sequencia)


def proxima_sequencia(ja_usados, faixa: str) -> int:
    """Onde começar a contar, olhando o que a loja JÁ tem.

    Começar sempre em 1 e sair pulando o ocupado funciona, mas dá numeração
    esburacada e fica lento em loja grande. Continuar de onde parou é o que o
    lojista espera ao rodar o gerador uma segunda vez.
    """
    faixa = (faixa or "").strip()
    maior = 0
    for valor in ja_usados or ():
        valor = str(valor or "").strip()
        if (len(valor) == TAMANHO_DO_GTIN and valor.isdigit()
                and valor.startswith(faixa)):
            maior = max(maior, int(valor[len(faixa):-1]))
    return maior + 1


def gerar_lote(itens, modo: str = "interno", prefixo: str = "",
               ja_usados=None) -> list:
    """O lote inteiro, com o motivo de cada um que ficou de fora.

    Uma linha por item, sempre na ordem recebida:

        {"item": ..., "codigo": "...", "tipo": "...", "pulado": "...",
         "aviso": "..."}

    Quem pula nunca some em silêncio — é a mesma regra da prévia da etiqueta.

    `ja_usados` são os códigos que a loja já tem, e entram na conferência de
    colisão. Dois produtos com o mesmo código bipam o produto errado no caixa, e
    essa é a pior falha que este app pode causar.
    """
    if modo not in MODOS:
        raise ValueError("modo %r não existe. Disponíveis: %s"
                         % (modo, ", ".join(sorted(MODOS))))
    if modo == "gs1":
        problemas = conferir_prefixo(prefixo)
        if problemas:
            raise ValueError("; ".join(problemas))

    faixa = prefixo.strip() if modo == "gs1" else FAIXA_INTERNA
    usados = {str(c).strip() for c in (ja_usados or ()) if str(c).strip()}
    proximo = proxima_sequencia(usados, faixa)
    teto = capacidade(faixa)

    saida = []
    for item in itens or []:
        atual = campos.resolver("variante.codigo_barras", item).strip()
        if atual:
            # Pode ser código comprado, impresso em caixa fechada. Trocar é
            # estrago sem volta, e silencioso.
            saida.append({"item": item, "codigo": atual, "tipo": "",
                          "pulado": "já tem código de barras", "aviso": ""})
            continue

        if modo == "sku":
            saida.append(_linha_do_sku(item, usados))
            continue

        codigo = ""
        while proximo <= teto:
            candidato = _montar(faixa, proximo)
            proximo += 1
            if candidato not in usados:
                codigo = candidato
                break

        if not codigo:
            # Dois motivos diferentes, e dizer "acabou" nos dois seria mentir
            # num deles.
            #
            # A numeração CONTINUA de onde a loja parou, em vez de encher
            # buraco — número reaproveitado faz uma etiqueta velha, já colada,
            # apontar pro produto de agora. O efeito colateral é que um prefixo
            # pequeno pode esgotar a continuação com números livres embaixo.
            # O lojista precisa saber qual dos dois aconteceu pra decidir.
            livres = teto - len([c for c in usados
                                 if len(c) == TAMANHO_DO_GTIN
                                 and c.startswith(faixa)])
            saida.append({"item": item, "codigo": "", "tipo": "", "aviso": "",
                          "pulado": _motivo_do_fim(faixa, teto, livres)})
            continue

        usados.add(codigo)
        saida.append({"item": item, "codigo": codigo, "tipo": MODOS[modo],
                      "pulado": "", "aviso": ""})

    return saida


def _motivo_do_fim(faixa: str, teto: int, livres: int) -> str:
    """Por que não saiu número: a faixa encheu, ou a contagem chegou ao fim?

    São coisas diferentes, e tratar as duas como "acabou" esconderia do lojista
    justamente a que ele pode resolver.
    """
    if livres <= 0:
        return ("o prefixo %s está cheio — ele comporta %d produtos no total"
                % (faixa, teto))
    return ("a numeração do prefixo %s chegou ao fim. Sobraram %d números "
            "livres abaixo do maior que você já usa, mas o gerador não "
            "reaproveita: uma etiqueta antiga já impressa passaria a apontar "
            "para outro produto" % (faixa, livres))


def _linha_do_sku(item, usados) -> dict:
    """Caso 3: o código é o próprio SKU, impresso como Code 128."""
    sku = campos.resolver("variante.sku", item).strip()
    if not sku:
        return {"item": item, "codigo": "", "tipo": "", "aviso": "",
                "pulado": "este produto não tem SKU — gere o SKU primeiro"}

    # Code 128 aceita ASCII imprimível, e só. SKU com acento sai da impressora
    # como outra coisa, ou não sai.
    vale, motivo = codigos.validar(sku, codigos.CODE128)
    if not vale:
        return {"item": item, "codigo": "", "tipo": "", "aviso": "",
                "pulado": "o SKU %s não vira código de barras: %s"
                          % (sku, motivo)}

    if sku in usados:
        # Dois produtos com o mesmo SKU já é um problema do catálogo. Virar
        # código de barras transforma isso em produto errado no caixa.
        return {"item": item, "codigo": "", "tipo": "", "aviso": "",
                "pulado": "o SKU %s está repetido na loja — dois produtos com o "
                          "mesmo código bipam errado no caixa" % sku}

    usados.add(sku)
    return {"item": item, "codigo": sku, "tipo": MODOS["sku"],
            "pulado": "", "aviso": ""}
