"""A tabela de lojas: quem instalou, com que token, em que plano.

Esta é a única tabela sem `loja_id` — ela **é** a loja. Todas as outras penduram
nela, e o `id` daqui é o que filtra o resto.

## Reinstalação não pode virar loja nova

Lojista desinstala e reinstala o tempo todo — troca de plano, testa outro app,
volta. Se cada instalação criasse uma linha, os modelos que a pessoa desenhou
ficariam presos na linha velha e ela abriria o app numa tela em branco, achando
que perdeu tudo.

Por isso o `dominio` é UNIQUE e `salvar()` é um upsert: reinstalar atualiza o
token e reativa a mesma linha, com os modelos todos lá.
"""
from datetime import datetime, timedelta, timezone

from . import banco
from loja import dominio as dom


def agora() -> str:
    """UTC sempre, em ISO. Loja pode estar em qualquer fuso; o banco não escolhe."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def daqui_a(segundos) -> str:
    """Um instante no futuro, em UTC ISO. Vazio quando não há prazo.

    O Shopify manda prazo RELATIVO (`expires_in: 3600`). Guardar o relativo não
    serve pra nada depois — o que a gente precisa saber, na próxima requisição,
    é se JÁ VENCEU. Então converte na hora de guardar, uma vez.
    """
    try:
        segundos = int(segundos)
    except (TypeError, ValueError):
        return ""
    if segundos <= 0:
        return ""
    return (datetime.now(timezone.utc)
            + timedelta(seconds=segundos)).isoformat(timespec="seconds")


def venceu(quando: str, margem_segundos: int = 0) -> bool:
    """Esse prazo já passou (ou passa dentro da margem)?

    Sem prazo devolve False: token antigo, sem `token_expira_em`, não é um token
    vencido — é um token de outro tipo, e quem cuida disso é a migração.
    """
    if not quando:
        return False
    try:
        limite = datetime.fromisoformat(quando)
    except (TypeError, ValueError):
        return True
    if limite.tzinfo is None:
        limite = limite.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc)
            + timedelta(seconds=max(0, margem_segundos))) >= limite


def guardar_credenciais(loja_id: int, token: str, refresh: str = "",
                        expira_em: str = "", refresh_expira_em: str = ""):
    """Troca o par token+refresh de uma loja já instalada.

    Usado pela renovação: o Shopify devolve um par NOVO a cada renovação e
    invalida o anterior, então guardar é obrigatório, não otimização. Perder o
    refresh novo deixa a loja órfã — sem acesso e sem como renovar — e a única
    saída vira reinstalar.
    """
    if not token:
        raise ValueError("não dá pra guardar credencial sem token de acesso")
    with banco.conectar() as con:
        con.execute(
            """UPDATE lojas
                  SET token_cifrado     = ?,
                      refresh_cifrado   = ?,
                      token_expira_em   = ?,
                      refresh_expira_em = ?
                WHERE id = ?""",
            (banco.cifrar(token), banco.cifrar(refresh) if refresh else "",
             expira_em or None, refresh_expira_em or None, int(loja_id)))


def salvar(dominio_bruto: str, token: str, escopos="", refresh: str = "",
           expira_em: str = "", refresh_expira_em: str = "") -> int:
    """Grava (ou atualiza) a loja e devolve o `id`. Idempotente.

    O domínio passa pelo `normalizar` aqui também, mesmo já tendo passado no
    OAuth. Redundância de propósito: se um dia alguém chamar isto de outro lugar,
    a validação continua existindo.
    """
    limpo = dom.normalizar(dominio_bruto)
    if not token:
        raise ValueError("não dá pra salvar loja sem token de acesso")

    cifrado = banco.cifrar(token)
    with banco.conectar() as con:
        con.execute(
            """INSERT INTO lojas (dominio, token_cifrado, escopos, instalada_em,
                                  refresh_cifrado, token_expira_em,
                                  refresh_expira_em)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(dominio) DO UPDATE SET
                   token_cifrado     = excluded.token_cifrado,
                   escopos           = excluded.escopos,
                   refresh_cifrado   = excluded.refresh_cifrado,
                   token_expira_em   = excluded.token_expira_em,
                   refresh_expira_em = excluded.refresh_expira_em,
                   ativa             = 1,
                   desinstalada_em   = NULL""",
            (limpo, cifrado, escopos, agora(),
             banco.cifrar(refresh) if refresh else "",
             expira_em or None, refresh_expira_em or None))
        linha = con.execute("SELECT id FROM lojas WHERE dominio = ?",
                            (limpo,)).fetchone()
    return int(linha["id"])


def _registro(linha) -> dict:
    """Uma linha do banco virando registro de loja, com os segredos decifrados."""
    registro = dict(linha)
    registro["token"] = banco.decifrar(registro.pop("token_cifrado"))
    guardado = registro.pop("refresh_cifrado", "") or ""
    registro["refresh"] = banco.decifrar(guardado) if guardado else ""
    registro["ativa"] = bool(registro["ativa"])
    return registro


def buscar(dominio_bruto: str):
    """A loja pelo domínio, ou None. O token já vem decifrado.

    Domínio inválido devolve None em vez de estourar: quem chama isto normalmente
    está tratando entrada da web, e lá o certo é 404, não 500.
    """
    try:
        limpo = dom.normalizar(dominio_bruto)
    except ValueError:
        return None

    with banco.conectar() as con:
        linha = con.execute("SELECT * FROM lojas WHERE dominio = ?",
                            (limpo,)).fetchone()
    if not linha:
        return None

    return _registro(linha)


def por_id(loja_id: int):
    with banco.conectar() as con:
        linha = con.execute("SELECT * FROM lojas WHERE id = ?",
                            (int(loja_id),)).fetchone()
    if not linha:
        return None
    return _registro(linha)


# Quanto tempo o plano guardado vale sem reconferir com o Shopify. O webhook
# avisa quando muda; isto é a rede de segurança pro dia em que o webhook se
# perder — e webhook se perde.
VALIDADE_DO_PLANO_EM_HORAS = 6


def marcar_plano(loja_id: int, plano: str):
    """Guarda o plano lido do Shopify, e anota QUANDO foi conferido.

    Isto é CACHE, não a verdade. Quem manda é a resposta do Shopify
    (`cobranca.plano_ativo`) — se o lojista cancelar, o banco daqui fica velho por
    alguns minutos, e liberar recurso pago com base nele seria entregar de graça.
    Serve pra pintar a tela sem uma ida à API a cada clique.
    """
    with banco.conectar() as con:
        con.execute("UPDATE lojas SET plano = ?, plano_conferido_em = ? WHERE id = ?",
                    (str(plano), agora(), int(loja_id)))


def marcar_plano_vencido(loja_id: int):
    """O plano mudou lá no Shopify: o que a gente tem não vale mais.

    **Apaga a data, não o plano.** A primeira versão escrevia a palavra
    "conferir" dentro da coluna `plano` — e como "conferir" não é um plano
    conhecido, o app caía no mais restrito e o lojista que ACABOU de pagar era
    rebaixado pro grátis. Em silêncio, e pra sempre, porque nada resolvia esse
    estado de volta.

    Guardando a validade separada, o plano conhecido sobrevive: ele continua
    valendo enquanto a gente pergunta ao Shopify qual é o novo.
    """
    with banco.conectar() as con:
        con.execute("UPDATE lojas SET plano_conferido_em = NULL WHERE id = ?",
                    (int(loja_id),))


def plano_venceu(registro) -> bool:
    """Está na hora de reconferir o plano com o Shopify?"""
    if not registro:
        return False
    quando = registro.get("plano_conferido_em")
    if not quando:
        return True
    try:
        lido = datetime.fromisoformat(quando)
    except (TypeError, ValueError):
        return True
    idade = datetime.now(timezone.utc) - lido
    return idade.total_seconds() > VALIDADE_DO_PLANO_EM_HORAS * 3600


def desativar(dominio_bruto: str):
    """`app/uninstalled`: apaga o token, guarda os modelos.

    O token morre no instante da desinstalação — mantê-lo no banco é guardar
    segredo inútil. Já os modelos ficam: se a pessoa voltar semana que vem, o
    trabalho dela está lá.
    """
    try:
        limpo = dom.normalizar(dominio_bruto)
    except ValueError:
        return
    with banco.conectar() as con:
        con.execute("""UPDATE lojas
                       SET ativa = 0, token_cifrado = '', refresh_cifrado = '',
                           token_expira_em = NULL, refresh_expira_em = NULL,
                           desinstalada_em = ?
                       WHERE dominio = ?""", (agora(), limpo))


def apagar(dominio_bruto: str):
    """`shop/redact`: apaga tudo mesmo. Sem volta.

    Os modelos e as impressões somem junto pelo ON DELETE CASCADE — desde que o
    `PRAGMA foreign_keys` esteja ligado, o que `banco.conectar()` faz em toda
    conexão. Se não estivesse, isto deixaria lixo órfão e a gente estaria
    respondendo "apaguei" pro Shopify sem ter apagado.
    """
    try:
        limpo = dom.normalizar(dominio_bruto)
    except ValueError:
        return
    with banco.conectar() as con:
        con.execute("DELETE FROM lojas WHERE dominio = ?", (limpo,))
