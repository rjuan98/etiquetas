"""Template indo e voltando de JSON, com versão e validação.

Este arquivo carrega a promessa central do produto: **o template é do lojista e
não muda sozinho.** O Shopify mudou a fonte de todo mundo numa atualização de
julho de 2026 e as etiquetas pararam de combinar — *"todas as minhas etiquetas
não combinam mais"*, nas palavras de quem escreveu a avaliação.

Como a promessa vira código:

O campo `esquema` grava em que versão o template foi escrito. Mudança de
comportamento exige versão nova e uma migração explícita — nunca alterar como a
versão antiga renderiza. O teste de arquivo-espelho é quem impede isso na
prática.

E a validação devolve **todos** os problemas de uma vez, não o primeiro. Quem
está montando etiqueta quer ver a lista inteira e resolver, não descobrir um
defeito por vez.
"""
import json
from dataclasses import fields

from . import campos, codigos, unidades
from .modelo import (Calibracao, CodigoBarras, Midia, Preco, Template, Texto)

ESQUEMA_ATUAL = 1

# O discriminador que vai no JSON. Sem ele não dá pra saber que classe recriar.
TIPOS = {
    "texto": Texto,
    "preco": Preco,
    "codigo_barras": CodigoBarras,
}
TIPO_POR_CLASSE = {classe: nome for nome, classe in TIPOS.items()}


# ------------------------------------------------------------------ escrever

def _elemento_para_dict(el) -> dict:
    """Serializa por introspecção, não por lista escrita à mão.

    Escrever os campos de novo aqui criaria duas listas pra manter em sincronia —
    e lista duplicada que desencontra é exatamente a família de bug que a gente
    passou uma semana consertando no Hércules.
    """
    # Preco herda de Texto, então a ordem de checagem importa: o mais específico
    # primeiro, senão todo preço vira texto.
    for classe in (Preco, CodigoBarras, Texto):
        if isinstance(el, classe):
            saida = {"tipo": TIPO_POR_CLASSE[classe]}
            for campo in fields(classe):
                saida[campo.name] = getattr(el, campo.name)
            return saida
    raise TypeError("elemento desconhecido: %r" % type(el))


def para_dict(template: Template) -> dict:
    return {
        "esquema": template.esquema,
        "nome": template.nome,
        "midia": {c.name: getattr(template.midia, c.name) for c in fields(Midia)},
        "calibracao": {c.name: getattr(template.calibracao, c.name)
                       for c in fields(Calibracao)},
        "elementos": [_elemento_para_dict(el) for el in template.elementos],
    }


def para_json(template: Template, identado=True) -> str:
    return json.dumps(para_dict(template), ensure_ascii=False,
                      indent=2 if identado else None)


# ------------------------------------------------------------------- ler

def _elemento_de_dict(bruto: dict):
    tipo = bruto.get("tipo")
    if tipo not in TIPOS:
        raise ValueError(
            "tipo de elemento %r não existe. Conhecidos: %s"
            % (tipo, ", ".join(sorted(TIPOS)))
        )
    classe = TIPOS[tipo]
    # Só o que a classe conhece. Campo a mais no JSON é ignorado de propósito:
    # template salvo por uma versão futura deve continuar abrindo aqui, sem
    # explodir por causa de um campo que este código ainda não entende.
    aceitos = {c.name for c in fields(classe)}
    return classe(**{k: v for k, v in bruto.items() if k in aceitos})


def de_dict(bruto: dict) -> Template:
    if not isinstance(bruto, dict):
        raise ValueError("esperava um template em JSON, veio %r" % type(bruto).__name__)
    bruto = migrar(bruto)
    midia_bruta = bruto.get("midia") or {}
    aceitos_midia = {c.name for c in fields(Midia)}
    cal_bruta = bruto.get("calibracao") or {}
    aceitos_cal = {c.name for c in fields(Calibracao)}

    return Template(
        nome=bruto.get("nome", "sem nome"),
        esquema=bruto.get("esquema", ESQUEMA_ATUAL),
        midia=Midia(**{k: v for k, v in midia_bruta.items() if k in aceitos_midia}),
        calibracao=Calibracao(**{k: v for k, v in cal_bruta.items() if k in aceitos_cal}),
        elementos=[_elemento_de_dict(e)
                   for e in (bruto.get("elementos") or [])
                   if isinstance(e, dict)],
    )


def de_json(texto: str) -> Template:
    return de_dict(json.loads(texto))


# --------------------------------------------------------------- migração

def migrar(bruto: dict) -> dict:
    """Traz um template antigo para o formato atual.

    Hoje só existe a versão 1, então isto não faz nada — e está aqui de
    propósito. Quando a versão 2 existir, a migração é escrita AQUI, e o
    template versão 1 continua renderizando exatamente como sempre renderizou.

    O que NÃO se faz nunca: mudar o comportamento da versão 1. É essa a promessa.
    """
    try:
        versao = int(bruto.get("esquema", 1))
    except (TypeError, ValueError):
        versao = 1                     # versão ilegível: trata como a primeira
    if versao > ESQUEMA_ATUAL:
        raise ValueError(
            "este template foi salvo numa versão mais nova do app (esquema %d, "
            "eu entendo até %d). Atualize o app pra abrir." % (versao, ESQUEMA_ATUAL)
        )
    # if versao == 1: bruto = _migrar_1_para_2(bruto)
    return bruto


# -------------------------------------------------------------- validação

def validar(template: Template, dpi: int = unidades.ZEBRA_203) -> list[str]:
    """Todos os problemas do template, em português, de uma vez.

    Devolve lista vazia quando está tudo certo.

    Vale mais que parece: descobrir que o código de barras passa 3mm da borda
    ANTES de imprimir custa uma mensagem na tela. Depois, custa um rolo de
    etiqueta e a paciência de quem colou 200 delas.
    """
    problemas = []
    m = template.midia

    if m.largura_mm <= 0 or m.altura_mm <= 0:
        problemas.append("a etiqueta precisa ter largura e altura maiores que zero")
    if m.tipo not in ("rolo", "folha"):
        problemas.append("tipo de mídia %r não existe (use 'rolo' ou 'folha')" % m.tipo)
    if m.tipo == "folha" and (m.colunas < 1 or m.linhas < 1):
        problemas.append("folha precisa de pelo menos 1 coluna e 1 linha")
    if not template.elementos:
        problemas.append("a etiqueta está vazia — arraste algum campo pra ela")

    for i, el in enumerate(template.elementos, 1):
        onde = "elemento %d" % i

        if el.campo and not campos.existe(el.campo):
            problemas.append("%s usa o campo %r, que não existe" % (onde, el.campo))

        if el.x_mm < 0 or el.y_mm < 0:
            problemas.append("%s está fora da etiqueta (posição negativa)" % onde)

        if isinstance(el, CodigoBarras):
            try:
                simb = codigos.obter(el.simbologia)
            except ValueError as erro:
                problemas.append("%s: %s" % (onde, erro))
                continue

            if el.altura_mm <= 0:
                problemas.append("%s: o código de barras precisa de altura" % onde)

            # A zona muda entra na conta: o código ocupa mais espaço do que a
            # largura visível das barras, e é aí que ele estoura a borda sem
            # ninguém perceber no editor.
            esq = codigos.margem_esquerda_mm(simb, el.modulo_dots, dpi)
            dir_ = codigos.margem_direita_mm(simb, el.modulo_dots, dpi)
            fim = el.x_mm + esq + el.largura_mm + dir_
            if fim > m.largura_mm:
                problemas.append(
                    "%s: o código de barras passa %.1fmm da borda direita "
                    "(contando a margem que o leitor exige)" % (onde, fim - m.largura_mm))
            if el.y_mm + el.altura_mm > m.altura_mm:
                problemas.append("%s: o código de barras passa da borda de baixo" % onde)

        elif isinstance(el, Texto):
            if el.tamanho_pt < 4:
                problemas.append(
                    "%s: fonte de %.1fpt é pequena demais pra ler" % (onde, el.tamanho_pt))
            if el.linhas_max < 1:
                problemas.append("%s: precisa de pelo menos 1 linha" % onde)
            if el.largura_mm and el.x_mm + el.largura_mm > m.largura_mm + 0.01:
                problemas.append(
                    "%s: o texto passa %.1fmm da borda direita"
                    % (onde, el.x_mm + el.largura_mm - m.largura_mm))
            if el.alinhamento not in ("esq", "dir", "centro"):
                problemas.append("%s: alinhamento %r não existe" % (onde, el.alinhamento))
            if el.excesso not in ("cortar", "encolher"):
                problemas.append(
                    "%s: %r não é uma saída pra texto que não cabe "
                    "(use 'cortar' ou 'encolher')" % (onde, el.excesso))

    return problemas


def valido(template: Template, dpi: int = unidades.ZEBRA_203) -> bool:
    return not validar(template, dpi)
