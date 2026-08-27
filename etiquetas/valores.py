"""O valor final de um elemento, já formatado. O ÚNICO lugar que decide isso.

Esta regra nasceu escrita duas vezes — inline no motor ZPL e como função no motor
PDF, com um comentário no PDF dizendo "mesma resolução do motor ZPL". O comentário
era a confissão: duas cópias que precisam concordar, e nada garantindo que
concordem.

O motor de prévia seria a terceira cópia. Aí extraí.

Não é zelo abstrato. Já aconteceu neste projeto: uma classe-embrulho quebrou o
`isinstance(el, Preco)` em silêncio, e o preço saiu "24.90" no PDF e "R$ 24,90"
no ZPL. A mesma etiqueta diferente conforme a impressora é exatamente o defeito
que este app existe pra corrigir.

Mora fora de `campos.py` de propósito: lá é "resolver um caminho num dicionário",
e não precisa saber que existem classes de elemento. Aqui é a camada acima.
"""
from . import campos
from .modelo import Preco


def do_elemento(el, dados: dict) -> str:
    """Campo resolvido + formatação de preço + prefixo e sufixo.

    Devolve "" quando o elemento tem campo mas o campo veio vazio — e isso leva o
    rótulo junto. "SKU: " sozinho numa etiqueta é pior que espaço em branco:
    parece defeito de impressão, e o lojista liga reclamando de uma etiqueta que
    tecnicamente saiu certa.

    Elemento sem campo é texto fixo, e aí prefixo e sufixo saem sozinhos.
    """
    if not el.campo:
        valor = ""
    elif isinstance(el, Preco):
        valor = campos.formatar_preco(
            campos.resolver(el.campo, dados),
            simbolo=el.simbolo, simbolo_depois=el.simbolo_depois,
            decimal=el.separador_decimal, milhar=el.separador_milhar,
        )
    else:
        valor = campos.resolver(el.campo, dados)

    if el.campo and not valor:
        return ""
    return el.prefixo + valor + el.sufixo
