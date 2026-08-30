"""O token de acesso da loja, sempre válido — ou o motivo de não ser.

## Por que este arquivo existe

O Shopify **parou de aceitar token de acesso que não expira**. A Admin API
responde `403` com a mensagem dizendo exatamente isso, e foi assim que o defeito
apareceu: o app instalado, a tela abrindo bonita, e nenhum produto carregando.

O token agora vale **1 hora** e vem com um `refresh_token` que vale **90 dias**.
Ou seja, o app deixou de ter uma credencial e passou a ter um ciclo de vida:

    instala  →  token (1h) + refresh (90d)
                    ↓ vence
                renova com o refresh  →  par NOVO, o anterior morre
                    ↓ refresh vence (90 dias sem ninguém abrir o app)
                reinstalar é a única saída

## Por que num lugar só

Cinco rotas chamavam `loja["token"]` direto. Espalhar a renovação por elas seria
garantir que a sexta esquecesse — e o sintoma de esquecer é o app funcionar por
uma hora depois de cada instalação e falhar depois, que é o pior tipo de bug:
some no teste e aparece no lojista.

Então a renovação mora no portão (`sessao.exige_loja`), e as rotas continuam
lendo `loja["token"]` sem saber que existe ciclo nenhum.

## As duas coisas que este arquivo conserta

**Token vencido.** Renova com o refresh, guarda o par novo.

**Token da era anterior.** Loja que instalou antes da mudança tem um token que
não expira e não tem refresh. Esse é TROCADO por um par novo, sem o lojista
fazer nada — o Shopify permite. A alternativa seria pedir pra reinstalar, e
lojista que precisa reinstalar pra o app voltar a funcionar desinstala e não
volta.
"""
from flask import current_app

from dados import lojas
from loja import oauth, rede
from . import config

# Quanto antes do vencimento a gente já renova. O token vale 1 hora; renovar com
# 5 minutos de folga evita a corrida em que o token vence ENTRE a conferência e a
# chamada ao Shopify — que aconteceria raramente e seria impossível de reproduzir.
MARGEM_EM_SEGUNDOS = 300


class PrecisaReinstalar(Exception):
    """O refresh morreu (ou o Shopify recusou). Só o lojista resolve agora."""


def _guardar(registro: dict, resposta: dict) -> dict:
    """Guarda o par novo e devolve o registro já atualizado.

    Guardar é obrigatório, não otimização: cada renovação invalida o par
    anterior. Perder o refresh novo deixa a loja órfã — sem acesso e sem como
    renovar.
    """
    novo = rede.credenciais_da_resposta(resposta)
    if not novo["token"]:
        raise PrecisaReinstalar("o Shopify não devolveu token na renovação")

    lojas.guardar_credenciais(registro["id"], novo["token"], novo["refresh"],
                              novo["expira_em"], novo["refresh_expira_em"])
    registro = dict(registro)
    registro["token"] = novo["token"]
    registro["refresh"] = novo["refresh"]
    registro["token_expira_em"] = novo["expira_em"]
    registro["refresh_expira_em"] = novo["refresh_expira_em"]
    return registro


def _pedir(url: str, corpo: dict, oque: str) -> dict:
    try:
        return rede.trocar_token(url, corpo)
    except rede.ErroDeRede as erro:
        # O corpo do erro pode trazer o token; o log leva só o que aconteceu.
        current_app.logger.error("%s falhou para a loja: %s", oque, erro)
        raise PrecisaReinstalar("%s falhou" % oque)


def garantir(registro: dict) -> dict:
    """O registro da loja com um token que o Shopify vai aceitar.

    Devolve o mesmo registro quando não há nada a fazer — que é o caso comum, e
    por isso não custa rede nenhuma.
    """
    if not registro or not registro.get("token"):
        return registro

    # Loja da era anterior: token sem prazo e sem refresh. Troca por um par novo.
    if not registro.get("refresh") and not registro.get("token_expira_em"):
        url, corpo = oauth.troca_do_token_antigo(
            registro["dominio"], config.CHAVE_API, config.SEGREDO,
            registro["token"])
        current_app.logger.info("trocando token antigo por um que expira")
        return _guardar(registro, _pedir(url, corpo, "a troca do token antigo"))

    if not lojas.venceu(registro.get("token_expira_em"), MARGEM_EM_SEGUNDOS):
        return registro

    # O token venceu. Se o refresh também venceu, não há o que fazer daqui: o
    # lojista precisa autorizar de novo. Dizer isso é melhor que tentar, tomar
    # 400 do Shopify e devolver "erro interno".
    if lojas.venceu(registro.get("refresh_expira_em")):
        raise PrecisaReinstalar("o refresh_token venceu")
    if not registro.get("refresh"):
        raise PrecisaReinstalar("não há refresh_token guardado")

    url, corpo = oauth.renovacao_de_token(
        registro["dominio"], config.CHAVE_API, config.SEGREDO,
        registro["refresh"])
    return _guardar(registro, _pedir(url, corpo, "a renovação do token"))
