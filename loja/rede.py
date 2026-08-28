"""O único arquivo do projeto que fala com a internet.

Todo o resto de `loja/` monta URL e corpo, e devolve — de propósito, pra ser
testável sem credencial. Aqui é onde isso vira requisição de verdade.

Ter um só lugar não é organização: é o que faz timeout, tentativa e limite de
requisição existirem **sempre**. Espalhado por dez rotas, alguma vai ficar sem
timeout, e um Shopify lento derruba o servidor inteiro com requisições penduradas.

## Sem `requests`

Só biblioteca padrão. Uma dependência a menos pra instalar no servidor, uma a
menos pra atualizar quando tiver falha de segurança, e pra POST de JSON o
`urllib` dá e sobra.

## O limite de requisições do Shopify

O GraphQL do Shopify usa um balde que enche: cada consulta custa pontos, o balde
repõe 50 por segundo. Estourou, ele responde 200 (não 429!) com `THROTTLED`
dentro do JSON. Quem só olha o código HTTP acha que deu certo e mostra tela vazia.

A espera é exponencial porque insistir no mesmo ritmo só afunda mais o balde.
"""
import json
import time
import urllib.error
import urllib.request

TEMPO_LIMITE = 20          # segundos por requisição
TENTATIVAS = 3
ESPERA_BASE = 1.0          # dobra a cada tentativa


class ErroDeRede(Exception):
    """Falha ao falar com o Shopify. Mensagem já em português, pro log."""


class _SemRedirecionamento(urllib.request.HTTPRedirectHandler):
    """Recusa redirecionamento.

    O `dominio.py` garante que a URL começa em `*.myshopify.com`, mas um
    redirecionamento aconteceria DEPOIS dessa checagem e levaria a requisição
    pra onde a resposta mandar — inclusive pra um endereço interno da rede do
    servidor. A API do Shopify não redireciona, então recusar não custa nada.
    """
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ErroDeRede("o Shopify respondeu com redirecionamento (%s), "
                         "o que não é esperado" % code)


def _montar_abridor():
    """O abridor, respeitando proxy do ambiente se houver.

    Hospedagem barata costuma obrigar a saída a passar por um proxy — o plano
    grátis do PythonAnywhere é assim, e é como ele controla a lista de sites
    permitidos.

    O `build_opener` só instala o `ProxyHandler` quando encontra proxy
    configurado no momento em que é chamado, e aqui isso acontece na importação
    do módulo. Num servidor que define `https_proxy` só pro processo do site, a
    variável pode não existir ainda — então o handler é montado explicitamente,
    e ele se vira sozinho quando não há proxy nenhum.

    Sem isto, o app subiria e falharia em TODA chamada ao Shopify, com erro de
    conexão e nada dizendo que o motivo é proxy.
    """
    return urllib.request.build_opener(
        urllib.request.ProxyHandler(), _SemRedirecionamento)


_abridor = _montar_abridor()


def _post(url: str, corpo: dict, cabecalhos: dict) -> dict:
    dados = json.dumps(corpo).encode("utf-8")
    pedido = urllib.request.Request(url, data=dados, method="POST")
    pedido.add_header("Content-Type", "application/json")
    for chave, valor in (cabecalhos or {}).items():
        pedido.add_header(chave, valor)

    try:
        with _abridor.open(pedido, timeout=TEMPO_LIMITE) as resposta:
            return json.loads(resposta.read().decode("utf-8"))
    except urllib.error.HTTPError as erro:
        detalhe = ""
        try:
            detalhe = erro.read().decode("utf-8")[:400]
        except Exception:
            pass
        raise ErroDeRede("o Shopify respondeu %s: %s" % (erro.code, detalhe))
    except urllib.error.URLError as erro:
        raise ErroDeRede("não consegui falar com o Shopify: %s" % erro.reason)
    except json.JSONDecodeError:
        raise ErroDeRede("o Shopify respondeu algo que não é JSON")


def _foi_estrangulado(resposta: dict) -> bool:
    """`THROTTLED` vem dentro de uma resposta 200, não num 429."""
    for erro in (resposta or {}).get("errors") or []:
        if isinstance(erro, dict):
            codigo = (erro.get("extensions") or {}).get("code")
            if codigo == "THROTTLED":
                return True
            if "throttled" in str(erro.get("message", "")).lower():
                return True
    return False


def graphql(loja: str, token: str, corpo: dict, tentativas: int = TENTATIVAS) -> dict:
    """Chama o GraphQL do admin, com espera crescente se levar limite.

    A URL passa pelo `catalogo.url_graphql`, que passa pelo `dominio.normalizar`.
    Montar essa string à mão aqui anularia a defesa contra SSRF.

    `tentativas` existe porque nem toda chamada merece insistir. O padrão de 3
    somado ao tempo limite dá **até 63 segundos** no pior caso — aceitável pra
    quem está esperando o catálogo carregar, e péssimo pra uma reconferida de
    cache que acontece dentro de um pedido de impressão. Quem só quer atualizar
    um valor que já tem passa `tentativas=1` e desiste rápido.
    """
    from . import catalogo

    if not token:
        raise ErroDeRede("loja sem token de acesso — precisa reinstalar o app")

    url = catalogo.url_graphql(loja)
    cabecalhos = {"X-Shopify-Access-Token": token}
    tentativas = max(1, int(tentativas))

    espera = ESPERA_BASE
    for tentativa in range(tentativas):
        resposta = _post(url, corpo, cabecalhos)
        if not _foi_estrangulado(resposta):
            return resposta
        if tentativa < tentativas - 1:
            time.sleep(espera)
            espera *= 2

    raise ErroDeRede("o Shopify está limitando as requisições. "
                     "Tente de novo em alguns segundos.")


def trocar_token(url: str, corpo: dict) -> dict:
    """Executa a troca do `code` do OAuth pelo token.

    Devolve o dicionário inteiro, não só o token, porque o RESTO diz que tipo de
    token é — e isso muda tudo:

      offline  o token não expira. É o que este app precisa: ele lê o catálogo
               quando o lojista manda imprimir, e responde webhook a qualquer
               hora, inclusive com ninguém logado.

      online   o token expira (~24h) e é amarrado ao usuário que instalou. Vem
               com `expires_in` e `associated_user` na resposta.

    Guardar um token online achando que é permanente é uma bomba-relógio: o app
    funciona no dia da instalação e no dia seguinte todo mundo vê erro, sem nada
    ter mudado. Por isso quem chama confere.
    """
    resposta = _post(url, corpo, {})
    token = (resposta or {}).get("access_token")
    if not token:
        raise ErroDeRede("o Shopify não devolveu o token de acesso")
    return resposta


def token_expira(resposta: dict) -> bool:
    """A resposta da troca descreve um token que expira?

    Vale só o que o **protocolo** diz: token por usuário vem com `expires_in` e
    `associated_user`; token permanente vem sem os dois.

    A primeira versão disto também tratava o prefixo `shpua_` como prova, e
    **deu alarme falso na primeira instalação de verdade**: o Shopify entregou
    um token `shpua_` sem `expires_in` nenhum. Prefixo é convenção da plataforma,
    muda sem aviso e não é contrato; `expires_in` é.

    A lição é a mesma que já apareceu neste projeto: medir com o sinal certo, não
    com o que parece.
    """
    if not isinstance(resposta, dict):
        return False
    return bool(resposta.get("expires_in") or resposta.get("associated_user"))
