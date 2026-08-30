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
from . import config, credenciais, textos


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

    # O token do Shopify passou a durar 1 hora. Renovar aqui, e não em cada
    # rota, é o que garante que a sexta rota escrita amanhã não esqueça — e o
    # sintoma de esquecer é o app funcionar por uma hora depois de instalar e
    # falhar depois. Ver `credenciais.py`.
    try:
        # A loja de mentira do MODO_DEV nao tem credencial de verdade pra
        # renovar — e tentar renovar sairia daqui pra internet, no unico modo
        # do app que existe pra rodar sem Shopify nenhum.
        from .dev import loja_de_mentira
        if not loja_de_mentira(registro):
            registro = credenciais.garantir(registro)
    except credenciais.PrecisaReinstalar as erro:
        g.motivo_do_token = str(erro)
        return None, "precisa_reinstalar"
    return registro, ""


# A chave do texto e o código HTTP. A frase mora em `textos.py`, como todas.
MENSAGENS = {
    "sem_token":      ("abrir_pelo_admin", 401),
    "token_invalido": ("sessao_expirada", 401),
    "nao_instalada":  ("nao_instalado", 403),
    "desinstalada":   ("desinstalado", 403),
    # A autorização morreu de velha (90 dias sem ninguém abrir o app) ou o
    # Shopify recusou renovar. Só o lojista resolve, autorizando de novo.
    "precisa_reinstalar": ("precisa_reinstalar", 403),
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
            chave, codigo = MENSAGENS.get(motivo, ("nao_autorizado", 401))
            idioma = getattr(g, "idioma", textos.PADRAO)
            return jsonify({"erro": textos.t(chave, idioma),
                            "motivo": motivo}), codigo
        return rota(*args, loja=registro, **kwargs)
    return dentro
