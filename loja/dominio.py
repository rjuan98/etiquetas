"""Validação do domínio da loja. O único lugar que decide se um `shop` é real.

Isto parece burocracia e é a peça de segurança mais importante do lado Shopify.

O nome da loja chega pela URL, em toda requisição: `?shop=minhaloja.myshopify.com`.
Ele é usado pra montar a URL de autorização, pra montar a chamada de API, e pra
achar o registro no banco. Se ele for aceito sem conferência, três coisas ruins
acontecem de uma vez:

**Redirecionamento pra qualquer lugar.** `?shop=site-do-golpe.com` faz o app
mandar o lojista pra uma tela de login falsa que parece o Shopify.

**Requisição saindo do servidor pra onde o atacante quiser** (SSRF). A API é
chamada em `https://{shop}/admin/api/...` — com um `shop` livre, o servidor vira
proxy do atacante.

**Envenenamento do banco.** Domínio com maiúscula, com barra no fim ou com porta
vira uma segunda linha pro mesmo lojista, e o app passa a ver duas lojas onde há
uma.

Por isso a regra é lista de permissão, não lista de bloqueio: **só passa o que
casa exatamente com o formato oficial.** Qualquer coisa fora disso é recusada,
sem tentar consertar.
"""
import re

# Só letras minúsculas, números e hífen, terminando em .myshopify.com.
# O Shopify permite de 3 a 60 caracteres no nome, sem hífen no começo ou no fim.
FORMATO = re.compile(r"^[a-z0-9][a-z0-9\-]{1,58}[a-z0-9]\.myshopify\.com$")

# As lojas de desenvolvimento e as "shopify.com" internas não entram aqui de
# propósito: o app só fala com loja de verdade, no domínio canônico.


def normalizar(bruto) -> str:
    """Devolve o domínio limpo, ou levanta erro. Nunca devolve algo duvidoso.

    Normalizar ANTES de validar é o que impede a mesma loja virar duas linhas no
    banco: "MinhaLoja.myshopify.com/" e "minhaloja.myshopify.com" são a mesma
    pessoa, e o banco precisa enxergar assim.
    """
    if not isinstance(bruto, str):
        raise ValueError("domínio da loja ausente")

    limpo = bruto.strip().lower()

    # Tira protocolo e caminho, que às vezes vêm colados.
    for prefixo in ("https://", "http://"):
        if limpo.startswith(prefixo):
            limpo = limpo[len(prefixo):]
    limpo = limpo.split("/")[0].split("?")[0]

    # Porta não existe em domínio de loja: se veio, é tentativa de contornar.
    if ":" in limpo:
        raise ValueError("domínio de loja inválido: %r" % bruto)

    if not FORMATO.match(limpo):
        raise ValueError("domínio de loja inválido: %r" % bruto)
    return limpo


def valido(bruto) -> bool:
    """Sim ou não, sem levantar erro. Pra quando a resposta é 404 e não 500."""
    try:
        normalizar(bruto)
        return True
    except ValueError:
        return False


def url_admin(loja: str, versao_api: str, recurso: str) -> str:
    """Monta a URL da API. Passa pelo `normalizar` de propósito.

    Toda URL que sai deste servidor em direção ao Shopify é montada aqui. Se
    alguém montar string à mão em outro arquivo, a validação deixa de existir na
    prática — e é assim que SSRF entra.
    """
    return "https://%s/admin/api/%s/%s" % (normalizar(loja), versao_api,
                                           recurso.lstrip("/"))
