"""Assinatura pelo Shopify App Pricing.

A vantagem grande desse caminho: **a cobrança entra na fatura que o lojista já
paga.** Ele não digita cartão, não cria conta, não passa por checkout. Vira uma
linha na conta do Shopify — e os próprios números do Shopify dizem que apps que
usam isso convertem mais de grátis pra pago, porque a cobrança vem de quem a
pessoa já confia.

E a comissão é zero até US$ 1 milhão de receita vitalícia. Depois, 15%. Apple e
Google levam 30% desde o primeiro centavo.

## Sobre os preços

O concorrente pago do nicho cobra US$ 5,99. Não vale brigar em preço — copiar o
valor dele deixa a gente sem margem e sem argumento. Melhor cobrar mais e
entregar o que ele não entrega: ZPL de verdade, calibração e versionamento de
template.
"""

VERSAO_API = "2026-07"

# O plano grátis existe pra pessoa provar que funciona ANTES de pagar. Sem ele, a
# primeira tela do app é uma cobrança, e ninguém instala nada assim.
PLANOS = {
    "gratis": {
        "nome": "Grátis",
        "preco_usd": 0.0,
        "limite_etiquetas_mes": 100,
        "templates": 1,
        "motores": ("pdf",),
        "resumo": "Folha adesiva, 1 modelo, 100 etiquetas por mês",
    },
    "pro": {
        "nome": "Pro",
        "preco_usd": 9.99,
        "limite_etiquetas_mes": 0,          # 0 = sem limite
        "templates": 0,
        "motores": ("pdf", "zpl"),
        "resumo": "Modelos ilimitados, impressora térmica, quantidade por regra",
    },
    "negocio": {
        "nome": "Negócio",
        "preco_usd": 19.99,
        "limite_etiquetas_mes": 0,
        "templates": 0,
        "motores": ("pdf", "zpl", "dymo"),
        "resumo": "Tudo do Pro, mais múltiplos locais e histórico de modelos",
    },
}

DIAS_DE_TESTE = 7

MUTACAO_ASSINAR = """
mutation assinar($nome: String!, $volta: URL!, $teste: Int, $preco: Decimal!,
                 $moeda: CurrencyCode!, $desenvolvimento: Boolean) {
  appSubscriptionCreate(
    name: $nome
    returnUrl: $volta
    trialDays: $teste
    test: $desenvolvimento
    lineItems: [{
      plan: { appRecurringPricingDetails: {
        price: { amount: $preco, currencyCode: $moeda }
        interval: EVERY_30_DAYS
      }}
    }]
  ) {
    confirmationUrl
    appSubscription { id status }
    userErrors { field message }
  }
}
""".strip()

CONSULTA_ASSINATURA = """
query { currentAppInstallation { activeSubscriptions { id name status } } }
""".strip()


def plano(codigo: str) -> dict:
    if codigo not in PLANOS:
        raise ValueError("plano %r não existe. Disponíveis: %s"
                         % (codigo, ", ".join(PLANOS)))
    return PLANOS[codigo]


def corpo_para_assinar(codigo: str, url_de_volta: str, desenvolvimento=False) -> dict:
    """O corpo da mutação. Sem rede, como o resto do módulo.

    `desenvolvimento=True` cria uma assinatura de teste, que não cobra nada. É
    obrigatório usar isso em loja de desenvolvimento — cobrar de verdade numa
    loja de teste é motivo de reprovação na revisão.
    """
    p = plano(codigo)
    if p["preco_usd"] <= 0:
        raise ValueError("o plano %r é grátis e não tem assinatura pra criar" % codigo)
    return {
        "query": MUTACAO_ASSINAR,
        "variables": {
            "nome": "Etiquetas — %s" % p["nome"],
            "volta": url_de_volta,
            "teste": DIAS_DE_TESTE,
            "preco": "%.2f" % p["preco_usd"],
            "moeda": "USD",
            "desenvolvimento": bool(desenvolvimento),
        },
    }


def url_de_confirmacao(resposta: dict) -> str:
    """Pra onde mandar o lojista pra ele aprovar a cobrança.

    Erro do Shopify vem em `userErrors` DENTRO de uma resposta 200 — quem só
    olha o código HTTP acha que deu certo e manda o lojista pra lugar nenhum.
    """
    dados = ((resposta or {}).get("data") or {}).get("appSubscriptionCreate") or {}
    erros = dados.get("userErrors") or []
    if erros:
        raise ValueError("; ".join(str(e.get("message", e)) for e in erros))
    url = dados.get("confirmationUrl")
    if not url:
        raise ValueError("o Shopify não devolveu a URL de confirmação")
    return url


def plano_ativo(resposta: dict) -> str:
    """Qual plano está ativo agora, lido da resposta do Shopify.

    O Shopify é a fonte da verdade sobre pagamento, não o nosso banco. Se a
    gente guardar "é pro" localmente e o lojista cancelar, o app continuaria
    liberando — e cobrar (ou entregar) errado é o tipo de erro que vira
    reclamação pública.
    """
    instalacao = ((resposta or {}).get("data") or {}).get("currentAppInstallation") or {}
    for assinatura in instalacao.get("activeSubscriptions") or []:
        if assinatura.get("status") != "ACTIVE":
            continue
        nome = (assinatura.get("name") or "").lower()
        for codigo, p in PLANOS.items():
            if p["preco_usd"] > 0 and p["nome"].lower() in nome:
                return codigo
    return "gratis"


def pode_usar(codigo_plano: str, motor: str) -> bool:
    """Este plano dá direito a este motor de impressão?"""
    return motor in plano(codigo_plano)["motores"]


def dentro_do_limite(codigo_plano: str, etiquetas_no_mes: int) -> bool:
    """Ainda cabe imprimir, ou o plano grátis estourou?"""
    limite = plano(codigo_plano)["limite_etiquetas_mes"]
    return limite == 0 or etiquetas_no_mes < limite
