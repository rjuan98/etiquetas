"""Prova de que a mensagem veio mesmo do Shopify. Só criptografia, sem rede.

Três coisas diferentes chegam assinadas, e cada uma tem seu jeito:

**Webhook** — o Shopify manda um POST e assina o corpo com HMAC-SHA256 no
cabeçalho `X-Shopify-Hmac-Sha256`. Sem conferir, qualquer um manda "desinstalei"
e apaga os dados de um lojista.

**Redirecionamento do OAuth** — os parâmetros da URL vêm assinados em `hmac`.
Sem conferir, dá pra forjar uma instalação.

**Token de sessão** — a tela embutida no admin manda um JWT a cada requisição.
Sem conferir, qualquer um se passa por qualquer lojista.

Todas as comparações usam `hmac.compare_digest`. Comparar assinatura com `==`
vaza informação pelo TEMPO da comparação: a igualdade normal para no primeiro
byte diferente, e medindo isso dá pra descobrir a assinatura byte a byte. É um
ataque real, e a defesa custa uma linha.
"""
import base64
import hashlib
import hmac
import json
import time

# Quanto de diferença de relógio a gente tolera no token de sessão. Servidor com
# hora levemente adiantada é comum; um minuto cobre isso sem abrir janela.
TOLERANCIA_RELOGIO = 60


def _lista(segredo) -> tuple:
    """Aceita um segredo ou vários. Existe por causa da rotação.

    Quando o Shopify rotaciona o Client secret, ele **continua assinando com o
    antigo** até a rotação ser concluída no painel. Com um segredo só, toda
    rotação derruba o app — e o sintoma é "recusado" sem motivo visível.

    Conferir contra os dois durante a janela é o comportamento certo. Note que
    isto vale só pra CONFERIR: o que a gente assina sai sempre com o atual.
    """
    if isinstance(segredo, str):
        return (segredo,) if segredo else ()
    return tuple(s for s in (segredo or ()) if s)


def _b64_decodificar(pedaco: str) -> bytes:
    """Base64 de URL, que o JWT usa sem o `=` do fim."""
    faltando = -len(pedaco) % 4
    return base64.urlsafe_b64decode(pedaco + "=" * faltando)


# ---------------------------------------------------------------- webhook

def webhook_confere(corpo: bytes, cabecalho_hmac: str, segredo: str) -> bool:
    """O corpo do webhook bate com a assinatura?

    O corpo tem que ser os BYTES CRUS, exatamente como chegaram. Se alguém ler o
    JSON e serializar de novo antes de conferir, a assinatura nunca mais bate —
    espaço a mais, ordem de chave diferente, e pronto. É o erro clássico aqui.
    """
    if not cabecalho_hmac:
        return False
    for s in _lista(segredo):
        calculado = base64.b64encode(
            hmac.new(s.encode("utf-8"), corpo, hashlib.sha256).digest()
        ).decode("utf-8")
        if hmac.compare_digest(calculado, cabecalho_hmac):
            return True
    return False


# ------------------------------------------------------------------ oauth

def parametros_conferem(parametros: dict, segredo: str) -> bool:
    """Os parâmetros da URL vieram mesmo do Shopify?

    A regra do Shopify: tira o `hmac` (e o `signature`, que é legado), ordena o
    resto por nome, junta como `chave=valor&...`, e assina.
    """
    recebido = parametros.get("hmac")
    if not recebido:
        return False

    resto = {k: v for k, v in parametros.items() if k not in ("hmac", "signature")}
    mensagem = "&".join("%s=%s" % (k, resto[k]) for k in sorted(resto))
    for s in _lista(segredo):
        calculado = hmac.new(s.encode("utf-8"), mensagem.encode("utf-8"),
                             hashlib.sha256).hexdigest()
        if hmac.compare_digest(calculado, recebido):
            return True
    return False


# ---------------------------------------------------------- token de sessão

class TokenInvalido(Exception):
    """Recusa explicada. A mensagem é pro log do dev, não pro lojista."""


def sessao_abrir(token: str, chave_api: str, segredo: str) -> dict:
    """Confere o JWT que a tela embutida manda e devolve o conteúdo.

    Cinco conferências, e **nenhuma delas é opcional** — cada uma fecha um jeito
    diferente de se passar por outro lojista:

    1. algoritmo é HS256, e vem do NOSSO lado, não do token
    2. a assinatura bate com o segredo do app
    3. `aud` é a nossa chave de API (senão é token de outro app)
    4. `exp` e `nbf` estão na janela (senão é token velho reaproveitado)
    5. `dest` é um domínio de loja de verdade

    A primeira é a mais traiçoeira: aceitar o algoritmo que o token declara
    permite o ataque do `alg: none`, em que o atacante manda um token sem
    assinatura nenhuma e a biblioteca aceita. Por isso o algoritmo é fixado aqui.
    """
    if not token or token.count(".") != 2:
        raise TokenInvalido("token de sessão malformado")

    cabecalho_b64, conteudo_b64, assinatura_b64 = token.split(".")

    try:
        cabecalho = json.loads(_b64_decodificar(cabecalho_b64))
        conteudo = json.loads(_b64_decodificar(conteudo_b64))
    except Exception:
        raise TokenInvalido("token de sessão ilegível")

    # 1. O algoritmo é NOSSO, não do token.
    if cabecalho.get("alg") != "HS256":
        raise TokenInvalido("algoritmo %r não é aceito" % cabecalho.get("alg"))

    # 2. Assinatura. Confere contra todos os segredos aceitos (ver `_lista`).
    recebida = assinatura_b64.rstrip("=")
    bate = False
    for s in _lista(segredo):
        esperada = base64.urlsafe_b64encode(
            hmac.new(s.encode("utf-8"),
                     ("%s.%s" % (cabecalho_b64, conteudo_b64)).encode("utf-8"),
                     hashlib.sha256).digest()
        ).decode("utf-8").rstrip("=")
        if hmac.compare_digest(esperada, recebida):
            bate = True
            break
    if not bate:
        raise TokenInvalido("assinatura do token não confere")

    # 3. O token é pra ESTE app.
    if conteudo.get("aud") != chave_api:
        raise TokenInvalido("token emitido para outro app")

    # 4. Janela de validade.
    agora = time.time()
    expira = conteudo.get("exp")
    if not isinstance(expira, (int, float)) or agora > expira + TOLERANCIA_RELOGIO:
        raise TokenInvalido("token de sessão expirado")
    comeca = conteudo.get("nbf")
    if isinstance(comeca, (int, float)) and agora < comeca - TOLERANCIA_RELOGIO:
        raise TokenInvalido("token de sessão ainda não vale")

    # 5. A loja de destino é real.
    from . import dominio
    try:
        conteudo["loja"] = dominio.normalizar(conteudo.get("dest", ""))
    except ValueError:
        raise TokenInvalido("token sem loja de destino válida")

    return conteudo


def sessao_assinar(conteudo: dict, segredo: str) -> str:
    """Monta um JWT HS256. Existe SÓ para os testes.

    Sem isto, testar a verificação exigiria um token real do Shopify — ou seja,
    exigiria conta, app instalado e loja de desenvolvimento. Com isto, toda a
    segurança é testável hoje, no computador, sem credencial nenhuma.
    """
    def parte(dados):
        return base64.urlsafe_b64encode(
            json.dumps(dados, separators=(",", ":")).encode("utf-8")
        ).decode("utf-8").rstrip("=")

    cabecalho = parte({"alg": "HS256", "typ": "JWT"})
    corpo = parte(conteudo)
    assinatura = base64.urlsafe_b64encode(
        hmac.new(segredo.encode("utf-8"),
                 ("%s.%s" % (cabecalho, corpo)).encode("utf-8"),
                 hashlib.sha256).digest()
    ).decode("utf-8").rstrip("=")
    return "%s.%s.%s" % (cabecalho, corpo, assinatura)
