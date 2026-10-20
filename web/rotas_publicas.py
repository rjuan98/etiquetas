"""Páginas públicas: política de privacidade e suporte.

Ficam **dentro do app**, servidas por ele, e não num Google Docs ou num Notion.
Três razões:

**A loja de apps exige uma URL de política de privacidade** e ela precisa estar
no ar sempre. Um link pra documento externo é mais uma coisa pra quebrar.

**A política tem que descrever o que o código faz de verdade.** Morando no mesmo
repositório, ela entra no mesmo commit que muda o comportamento — e quando
divergir, diverge à vista, no diff.

**Sem token de sessão.** Um revisor do Shopify, ou um lojista decidindo se
instala, precisa conseguir ler antes de instalar qualquer coisa.

## O que está escrito aqui é verificável

Cada afirmação sobre dado corresponde a uma linha do esquema em `dados/banco.py`
e à lista de escopos em `loja/oauth.py`. Se alguém acrescentar uma coluna que
guarde dado de cliente, esta página passa a mentir — e tem teste comparando as
duas coisas.
"""
from flask import Blueprint, render_template_string, g, request

from . import config, textos

rotas = Blueprint("publicas", __name__)

# Preenchidos pelo ambiente. Ficam de fora do código porque são dados do
# negócio, não do programa — e porque um endereço de e-mail no repositório vira
# alvo de robô de spam.
def _contato():
    return {
        "email": config.EMAIL_SUPORTE or "(preencha CONTATO_EMAIL no .env)",
        "responsavel": config.NOME_RESPONSAVEL or "(preencha CONTATO_NOME no .env)",
        "hospedagem": config.NOME_HOSPEDAGEM or "(preencha HOSPEDAGEM no .env)",
    }


MOLDE = """<!doctype html>
<html lang="{{ idioma }}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ titulo }}</title>
<style>
 body{font:16px/1.65 -apple-system,"Segoe UI",system-ui,sans-serif;color:#303030;
      background:#fff;margin:0;padding:40px 20px 80px}
 main{max-width:44rem;margin:0 auto}
 h1{font-size:26px;margin:0 0 6px;line-height:1.25}
 .data{color:#616161;font-size:14px;margin:0 0 32px}
 h2{font-size:18px;margin:34px 0 10px}
 p,li{margin:0 0 12px} ul{padding-left:22px}
 .caixa{background:#f6f6f7;border-radius:10px;padding:16px 18px;margin:20px 0}
 .caixa p:last-child{margin:0}
 code{font:14px ui-monospace,Consolas,monospace;background:#f1f2f4;
      border-radius:4px;padding:1px 5px}
 a{color:#005bd3} strong{font-weight:650}
 .idiomas{font-size:14px;margin:0 0 26px}
 footer{margin:44px 0 0;padding:18px 0 0;border-top:1px solid #e1e3e5;
        color:#616161;font-size:14px}
</style></head><body><main>
<p class="idiomas"><a href="?lang=en">English</a> · <a href="?lang=pt">Português</a></p>
{{ corpo|safe }}
<footer>{{ rodape|safe }}</footer>
</main></body></html>"""


PRIVACIDADE = {
"en": """
<h1>Privacy Policy</h1>
<p class="data">Last updated: %(data)s</p>

<p>This app prints barcode and price labels from the products already in your
Shopify store. This page explains exactly what it reads, what it stores, and
what it deliberately never touches.</p>

<div class="caixa">
<p><strong>The short version.</strong> The app reads your products and inventory
to build labels. It stores your label templates and a count of how many labels
you printed. It never reads or stores customer data, orders, or addresses — and
it never asks Shopify for permission to.</p>
</div>

<h2>What the app is allowed to access</h2>
<p>When you install it, Shopify asks you to approve exactly two permissions:</p>
<ul>
<li><code>read_products</code> — product title, variant, SKU, barcode, price and
vendor, so they can be placed on a label</li>
<li><code>read_inventory</code> — the stock count, used only to suggest how many
labels to print for each item</li>
</ul>
<p>Both are <strong>read-only</strong>. The app cannot change anything in your
store. You can verify this yourself in your Shopify admin, under Apps → this app
→ Activity and permissions.</p>
<p>It never requests access to customers, orders, shipping addresses,
checkout, or payments.</p>

<h2>What is stored on our server</h2>
<ul>
<li>Your store's <code>.myshopify.com</code> domain</li>
<li>The Shopify access token and its renewal token, both
<strong>encrypted</strong>, so the app can read your catalog when you ask it to
print. Shopify access tokens expire after an hour, so the app has to be able to
renew its own access; it cannot do anything with them that you did not
authorize at install</li>
<li>Which plan your store is on</li>
<li>The label templates you design: their layout, which fields you turned on,
your currency and calibration settings, and any fixed text you typed</li>
<li><strong>Only when you ask the app to fill in a missing SKU or barcode:</strong>
the variant, the value that was there before, and the value written. This exists
so you can undo it, it covers only what the app itself wrote — never a copy of
your catalog — and it is <strong>deleted after 30 days</strong>. If you never use
that feature, nothing of this is stored</li>
<li>A count of labels generated, with the date and the printer type — the number
only, never what was on the labels</li>
</ul>

<h2>What is never stored</h2>
<ul>
<li>Customer names, emails, addresses or any personal data of your buyers</li>
<li>Orders, payments or checkout information</li>
<li>Your product catalog. Products are read from Shopify at the moment you
press print and sent straight to your browser. They are never written to our
database</li>
</ul>
<p>Because of this, when Shopify asks the app to produce or erase data about one
of your customers, the honest answer is that there is nothing to produce or
erase.</p>

<h2>Your own personal data</h2>
<p>Shopify makes the store owner's name, email, phone and address available to
any installed app. This app does not request, read or store them. Your Shopify
admin discloses this for every app, which is why you may see it listed there.</p>

<h2>How long it is kept</h2>
<ul>
<li><strong>When you uninstall</strong>, both the access token and the renewal
token are deleted immediately, and the app can no longer reach your store. Your templates are kept, so that
reinstalling doesn't lose your work.</li>
<li><strong>48 hours after uninstalling</strong>, Shopify asks the app to erase
the store. Everything above — templates, counts, the store record itself — is
deleted permanently.</li>
<li>You can ask for deletion earlier, by email.</li>
</ul>

<h2>Who else touches the data</h2>
<ul>
<li><strong>Shopify</strong>, which is the source of the data and the party you
already have a relationship with.</li>
<li><strong>%(hospedagem)s</strong>, where the application runs.</li>
</ul>
<p>There are no analytics services, no advertising networks, and no third party
receiving your data. Nothing is sold or shared.</p>

<h2>Security</h2>
<ul>
<li>The access token is encrypted at rest, with a key that is not stored
alongside the database.</li>
<li>Every request is authenticated with a Shopify session token, and every
database query is filtered by store — one merchant cannot reach another's
templates.</li>
<li>All traffic uses HTTPS.</li>
</ul>
<p>No system is perfectly safe, and claiming otherwise would be dishonest. What
we can say is that the app holds very little that is worth stealing.</p>

<h2>Technical logs</h2>
<p>The server keeps ordinary access logs — date, store domain, and the address
requested — to diagnose failures. If you use the product search, the term you
typed may appear in those logs. They are kept for a short period and are not
used for anything else.</p>

<h2>Your rights</h2>
<p>You can ask, at any time, what is stored about your store, ask for a copy, or
ask for it to be deleted. Write to <a href="mailto:%(email)s">%(email)s</a> and
we will reply within 30 days. This covers requests under the GDPR and the
Brazilian LGPD.</p>

<h2>Changes</h2>
<p>If this policy changes, the date at the top changes with it. Changes that
affect what is collected will be announced inside the app before taking effect.</p>
""",

"pt": """
<h1>Política de Privacidade</h1>
<p class="data">Atualizada em: %(data)s</p>

<p>Este app imprime etiquetas de código de barras e preço a partir dos produtos
que já existem na sua loja Shopify. Esta página explica exatamente o que ele lê,
o que guarda, e o que ele deliberadamente nunca toca.</p>

<div class="caixa">
<p><strong>A versão curta.</strong> O app lê seus produtos e seu estoque pra
montar etiquetas. Ele guarda os seus modelos de etiqueta e a contagem de quantas
você imprimiu. Ele nunca lê nem guarda dado de cliente, pedido ou endereço — e
nunca pede permissão ao Shopify pra isso.</p>
</div>

<h2>O que o app pode acessar</h2>
<p>Na instalação, o Shopify pede que você aprove exatamente duas permissões:</p>
<ul>
<li><code>read_products</code> — título, variante, SKU, código de barras, preço e
fornecedor do produto, pra poderem ir na etiqueta</li>
<li><code>read_inventory</code> — a quantidade em estoque, usada só pra sugerir
quantas etiquetas imprimir de cada item</li>
</ul>
<p>As duas são <strong>somente leitura</strong>. O app não consegue alterar nada
na sua loja. Você pode conferir isso no seu painel do Shopify, em Apps → este app
→ Atividade e permissões.</p>
<p>Ele nunca pede acesso a clientes, pedidos, endereços de entrega, checkout ou
pagamentos.</p>

<h2>O que fica guardado no nosso servidor</h2>
<ul>
<li>O domínio <code>.myshopify.com</code> da sua loja</li>
<li>O token de acesso do Shopify e o token de renovação dele, os dois
<strong>cifrados</strong>, pra que o app consiga ler seu catálogo quando você
mandar imprimir. Token de acesso do Shopify vence em uma hora, então o app
precisa conseguir renovar o próprio acesso; ele não faz com eles nada além do
que você autorizou na instalação</li>
<li>Em que plano sua loja está</li>
<li>Os modelos de etiqueta que você desenha: o desenho, quais campos você ligou,
suas escolhas de moeda e calibração, e qualquer texto fixo que você digitou</li>
<li><strong>Só quando você pede ao app para preencher um SKU ou código que
falta:</strong> a variante, o valor que estava lá antes e o valor gravado. Isso
existe para você poder desfazer, cobre apenas o que o próprio app escreveu —
nunca uma cópia do seu catálogo — e é <strong>apagado em 30 dias</strong>. Se
você nunca usar esse recurso, nada disso é guardado</li>
<li>A contagem de etiquetas geradas, com a data e o tipo de impressora — só o
número, nunca o que estava escrito nelas</li>
</ul>

<h2>O que nunca é guardado</h2>
<ul>
<li>Nome, e-mail, endereço ou qualquer dado pessoal dos seus compradores</li>
<li>Pedidos, pagamentos ou informação de checkout</li>
<li>Seu catálogo de produtos. Os produtos são lidos do Shopify no momento em que
você manda imprimir e vão direto pro seu navegador. Eles nunca são gravados no
nosso banco</li>
</ul>
<p>Por causa disso, quando o Shopify pede ao app os dados de um cliente seu, ou
manda apagá-los, a resposta honesta é que não há nada pra entregar nem pra apagar.</p>

<h2>Os seus dados pessoais</h2>
<p>O Shopify disponibiliza nome, e-mail, telefone e endereço do titular da loja a
qualquer app instalado. Este app não pede, não lê e não guarda esses dados. Seu
painel do Shopify informa isso sobre todo app, e é por isso que você pode ver
essa menção lá.</p>

<h2>Por quanto tempo</h2>
<ul>
<li><strong>Quando você desinstala</strong>, o token de acesso e o de renovação
são apagados na hora, e o app deixa de alcançar sua loja. Seus modelos ficam guardados, pra que
reinstalar não perca seu trabalho.</li>
<li><strong>48 horas após desinstalar</strong>, o Shopify manda o app apagar a
loja. Tudo acima — modelos, contagens e o próprio registro da loja — é apagado
em definitivo.</li>
<li>Você pode pedir a exclusão antes disso, por e-mail.</li>
</ul>

<h2>Quem mais toca nesses dados</h2>
<ul>
<li><strong>O Shopify</strong>, que é a origem dos dados e com quem você já tem
uma relação.</li>
<li><strong>%(hospedagem)s</strong>, onde o app roda.</li>
</ul>
<p>Não há serviço de análise, não há rede de anúncios, e não há terceiro
recebendo seus dados. Nada é vendido nem compartilhado.</p>

<h2>Segurança</h2>
<ul>
<li>O token de acesso é cifrado em repouso, com uma chave que não fica guardada
junto do banco.</li>
<li>Toda requisição é autenticada com token de sessão do Shopify, e toda consulta
ao banco é filtrada por loja — um lojista não alcança os modelos de outro.</li>
<li>Todo o tráfego usa HTTPS.</li>
</ul>
<p>Nenhum sistema é perfeitamente seguro, e afirmar o contrário seria desonesto.
O que dá pra dizer é que este app guarda muito pouca coisa que valha a pena
roubar.</p>

<h2>Registros técnicos</h2>
<p>O servidor mantém registros de acesso comuns — data, domínio da loja e o
endereço requisitado — pra diagnosticar falhas. Se você usar a busca de produtos,
o termo digitado pode aparecer nesses registros. Eles são mantidos por pouco
tempo e não são usados pra mais nada.</p>

<h2>Seus direitos</h2>
<p>Você pode pedir, a qualquer momento, o que está guardado sobre a sua loja,
pedir uma cópia, ou pedir a exclusão. Escreva para
<a href="mailto:%(email)s">%(email)s</a> e respondemos em até 30 dias. Isso
cobre pedidos sob o GDPR e sob a LGPD.</p>

<h2>Alterações</h2>
<p>Se esta política mudar, a data no topo muda junto. Mudanças que afetem o que é
coletado serão avisadas dentro do app antes de valer.</p>
""",
}

RODAPE = {
    "en": "Operated by %(responsavel)s. Questions: "
          '<a href="mailto:%(email)s">%(email)s</a>.',
    "pt": "Operado por %(responsavel)s. Dúvidas: "
          '<a href="mailto:%(email)s">%(email)s</a>.',
}

ATUALIZADA_EM = "2026-08-28"


def _idioma():
    """`?lang=` manda, porque esta página tem botão de trocar idioma."""
    pedido = request.args.get("lang")
    if pedido:
        return textos.idioma_de(pedido)
    return getattr(g, "idioma", textos.PADRAO)


@rotas.get("/privacy")
@rotas.get("/privacidade")
def privacidade():
    idioma = _idioma()
    dados = dict(_contato(), data=ATUALIZADA_EM)
    return render_template_string(
        MOLDE, idioma=idioma,
        titulo="Privacy Policy" if idioma == "en" else "Política de Privacidade",
        corpo=PRIVACIDADE[idioma] % dados,
        rodape=RODAPE[idioma] % dados)
