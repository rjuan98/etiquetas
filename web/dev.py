"""Modo de desenvolvimento: a tela rodando sem Shopify nenhum.

## Por que isto existe

A tela usa o App Bridge pra pedir o token de sessão, e o App Bridge só existe
dentro do admin do Shopify. Sem um substituto, a tela só poderia ser vista depois
de: criar conta de Partner, criar loja de desenvolvimento, publicar o app num
endereço https e instalar.

Ou seja: eu escreveria a tela inteira sem nunca ter visto ela funcionar. É
exatamente o tipo de trabalho que parece pronto e não está.

Com isto, `MODO_DEV=1` sobe a tela completa no computador, com uma loja de
mentira e um catálogo de mentira, e **todo o resto do caminho é o de verdade** —
a mesma verificação de token, as mesmas rotas, o mesmo motor, o mesmo banco.

## O que é falso aqui, e só aqui

  1. a loja de mentira no banco, com token "dev-..."
  2. o `shopify.idToken()` do navegador, que passa a devolver um token que a
     gente mesmo assina
  3. o catálogo, que vem de uma lista fixa em vez do GraphQL

Nada disso é atalho de segurança: o token continua sendo conferido pelo mesmo
`assinatura.sessao_abrir()`, com as cinco checagens. Se a verificação quebrar, o
modo de desenvolvimento quebra junto — que é o que a gente quer.

## E isto NUNCA sobe em produção

O blueprint só é registrado se `MODO_DEV` estiver ligado, e o `config.exigir()`
recusa `MODO_DEV` junto com uma `APP_URL` de verdade. Duas trancas, porque uma
só bastaria pra alguém publicar sem perceber.
"""
import time

from flask import Blueprint, render_template_string, jsonify

from loja import assinatura
from dados import lojas
from . import config
from .rotas_tela import CASCA

rotas = Blueprint("dev", __name__, url_prefix="/dev")

LOJA = "loja-de-teste.myshopify.com"
TOKEN_FALSO = "dev-token-sem-valor"

# Catálogo de mentira, escolhido pra ser difícil de propósito: título gigante,
# produto sem código de barras, código com dígito verificador errado, preço com
# milhar, e uma variante com SKU comprido. Catálogo bonitinho esconde defeito.
CATALOGO_FALSO = [
    {"produto": {"titulo": "Canudo de Vidro Reto 20cm - Kit 4 unidades Reutilizável",
                 "fornecedor": "EcoVida", "tipo": "Canudo", "url": ""},
     "variante": {"id": "v1", "titulo": "Transparente / 20cm", "sku": "CAN-VD-20",
                  "codigo_barras": "7891234567895", "preco": "24.90",
                  "preco_comparado": "34.90", "estoque": 40, "url": ""}},
    {"produto": {"titulo": "Caneca de Porcelana Branca 300ml",
                 "fornecedor": "Cerâmica Real", "tipo": "Caneca", "url": ""},
     "variante": {"id": "v2", "titulo": "Branca / 300ml", "sku": "CAN-BR-300",
                  "codigo_barras": "7899876543210", "preco": "39.90",
                  "preco_comparado": "", "estoque": 12, "url": ""}},
    {"produto": {"titulo": "Camiseta P&B Estampada", "fornecedor": "Malharia Sul",
                 "tipo": "Camiseta", "url": ""},
     "variante": {"id": "v3", "titulo": "Preta / M", "sku": "CAM-PB-M-LONGO-DEMAIS",
                  "codigo_barras": "", "preco": "1249.90",
                  "preco_comparado": "", "estoque": 3, "url": ""}},
    {"produto": {"titulo": "Vaso de Cerâmica", "fornecedor": "", "tipo": "", "url": ""},
     "variante": {"id": "v4", "titulo": "Bege / P", "sku": "VAS-BG-P",
                  "codigo_barras": "7891234567890",     # verificador ERRADO, de propósito
                  "preco": "89.00", "preco_comparado": "", "estoque": 7, "url": ""}},
]

# Injeta o substituto do App Bridge. Assina com o segredo do app, exatamente como
# o Shopify faria — então o `sessao_abrir()` do outro lado não sabe a diferença,
# e continua fazendo as cinco conferências.
REMENDO = """
<script>
window.shopify = {
  idToken: async function () {
    const r = await fetch("/dev/token");
    return (await r.json()).token;
  }
};
</script>
"""


def _garantir_loja():
    registro = lojas.buscar(LOJA)
    if not registro or not registro["ativa"]:
        lojas.salvar(LOJA, TOKEN_FALSO, "read_products,read_inventory")
    return lojas.buscar(LOJA)


@rotas.get("/")
def tela():
    """A tela de verdade, com o App Bridge substituído."""
    _garantir_loja()
    pagina = render_template_string(CASCA, chave_api=config.CHAVE_API)
    # Entra ANTES do script da tela, senão `shopify` ainda não existe na hora
    # em que `comecar()` roda.
    return pagina.replace(
        '<script src="https://cdn.shopify.com/shopifycloud/app-bridge.js"></script>',
        REMENDO)


@rotas.get("/token")
def token():
    """Um token de sessão válido pra loja de mentira.

    Dura 5 minutos, como os de verdade. Se durasse horas, eu não veria o caso em
    que o token expira no meio do uso — que é um bug real que o lojista teria.
    """
    _garantir_loja()
    agora = time.time()
    return jsonify({"token": assinatura.sessao_assinar({
        "iss": "https://%s/admin" % LOJA,
        "dest": "https://%s" % LOJA,
        "aud": config.CHAVE_API,
        "sub": "1",
        "exp": agora + 300,
        "nbf": agora - 5,
        "iat": agora,
    }, config.SEGREDO)})


def catalogo_falso(busca=None):
    """O catálogo de mentira, filtrado pela busca. Usado por `/api/produtos`."""
    if not busca:
        return list(CATALOGO_FALSO)
    alvo = busca.strip().lower()
    return [i for i in CATALOGO_FALSO
            if alvo in i["produto"]["titulo"].lower()
            or alvo in (i["variante"]["sku"] or "").lower()
            or alvo in (i["variante"]["codigo_barras"] or "")]


def loja_de_mentira(registro) -> bool:
    """Esta loja é a de desenvolvimento?

    O `MODO_DEV` sozinho não basta: com ele ligado e uma loja de verdade
    instalada, o catálogo falso apareceria no lugar do catálogo dela.
    """
    return bool(config.MODO_DEV) and registro.get("token") == TOKEN_FALSO
