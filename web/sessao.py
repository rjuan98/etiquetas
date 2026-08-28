"""Quem está chamando, e de que loja. O portão de toda rota de dados.

## Por que não é cookie

O app roda dentro de um `<iframe>` no admin do Shopify. Cookie ali é cookie de
terceiro, e Safari e Firefox bloqueiam por padrão — o app funcionaria no Chrome
do desenvolvedor e falharia no Mac do lojista, que é o pior tipo de bug: só
acontece com quem paga.

Por isso o Shopify usa **token de sessão**: um JWT curto que a tela pede ao App
Bridge e manda em `Authorization: Bearer ...` a cada requisição. Não depende de
cookie, dura ~1 minuto, e diz de que loja veio.

## A regra que não pode ter exceção

Nenhuma rota de dados descobre a loja pela URL. Se `/api/produtos?loja=X`
funcionasse, qualquer um trocaria o X e leria o catálogo alheio. A loja vem
**só** do token assinado, e o `loja_id` que vai pro banco vem daí.

O decorador injeta `loja` como argumento pra que a rota não tenha como esquecer:
ela recebe a loja pronta ou não roda.
"""
from functools import wraps

from flask import request, jsonify, g

from loja import assinatura
from dados import lojas
from . import config


def _token_do_cabecalho() -> str:
    bruto = request.headers.get("Authorization", "")
    if bruto.lower().startswith("bearer "):
        return bruto[7:].strip()
    return ""


def loja_atual():
    """A loja do token, ou (None, motivo).

    Devolve motivo em vez de só None porque os três casos pedem resposta
    diferente na tela: token vencido é "recarregue", loja inativa é "reinstale",
    e sem token é "abra pelo admin do Shopify".
    """
    token = _token_do_cabecalho()
    if not token:
        return None, "sem_token"

    try:
        conteudo = assinatura.sessao_abrir(token, config.CHAVE_API,
                                           config.segredos_aceitos())
    except assinatura.TokenInvalido as erro:
        # O motivo detalhado fica no log; pro chamador vai só a categoria.
        # Dizer "assinatura não confere" vs "expirado" ajuda quem está atacando
        # a saber em que ponto parou.
        g.motivo_do_token = str(erro)
        return None, "token_invalido"

    registro = lojas.buscar(conteudo["loja"])
    if not registro:
        return None, "nao_instalada"
    if not registro["ativa"]:
        return None, "desinstalada"
    return registro, ""


MENSAGENS = {
    "sem_token":     ("Abra o app pelo painel do Shopify.", 401),
    "token_invalido": ("Sessão expirada. Recarregue a página.", 401),
    "nao_instalada": ("Este app não está instalado nesta loja.", 403),
    "desinstalada":  ("O app foi desinstalado desta loja. Instale de novo.", 403),
}


def exige_loja(rota):
    """Só deixa passar quem tem token válido, e entrega a loja pronta.

    Injetar `loja` como argumento é de propósito: se o decorador só validasse e
    a rota buscasse a loja por conta própria, uma rota nova poderia esquecer de
    filtrar. Assim, o caminho fácil é o certo.
    """
    @wraps(rota)
    def dentro(*args, **kwargs):
        registro, motivo = loja_atual()
        if not registro:
            texto, codigo = MENSAGENS.get(motivo, ("Não autorizado.", 401))
            return jsonify({"erro": texto, "motivo": motivo}), codigo
        return rota(*args, loja=registro, **kwargs)
    return dentro
