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

from flask import Blueprint, render_template_string, jsonify, g, request

from loja import assinatura
from dados import lojas
from . import config, textos
from .rotas_tela import CASCA

rotas = Blueprint("dev", __name__, url_prefix="/dev")

LOJA = "loja-de-teste.myshopify.com"
TOKEN_FALSO = "dev-token-sem-valor"

# Catálogo de mentira, escolhido pra ser difícil de propósito: título gigante,
# produto sem código de barras, código com dígito verificador errado, preço com
# milhar, e uma variante com SKU comprido. Catálogo bonitinho esconde defeito.
# Em inglês porque é a língua do mercado que a gente mediu, e porque estas são as
# telas que viram captura na loja de apps. Cada item continua sendo um caso
# difícil de propósito — catálogo bonitinho esconde defeito.
CATALOGO_FALSO = [
    # título longo: exercita a quebra em duas linhas
    {"produto": {"titulo": "Reusable Glass Straw Set — 4 pieces with cleaning brush",
                 "fornecedor": "EcoVida", "tipo": "Drinkware", "url": ""},
     "variante": {"id": "v1", "titulo": "Clear / 20cm", "sku": "STRW-GL-20",
                  "codigo_barras": "7891234567895", "preco": "24.90",
                  "preco_comparado": "34.90", "estoque": 40, "url": ""}},
    {"produto": {"titulo": "White Porcelain Mug 300ml",
                 "fornecedor": "Real Ceramics", "tipo": "Drinkware", "url": ""},
     "variante": {"id": "v2", "titulo": "White / 300ml", "sku": "MUG-WH-300",
                  "codigo_barras": "7899876543210", "preco": "39.90",
                  "preco_comparado": "", "estoque": 12, "url": ""}},
    # sem código de barras, e SKU comprido de propósito
    {"produto": {"titulo": "Organic Cotton T-Shirt", "fornecedor": "Sul Knitwear",
                 "tipo": "Apparel", "url": ""},
     "variante": {"id": "v3", "titulo": "Black / M", "sku": "TSH-ORG-BLK-M-LONG",
                  "codigo_barras": "", "preco": "1249.90",
                  "preco_comparado": "", "estoque": 3, "url": ""}},
    {"produto": {"titulo": "Ceramic Plant Pot", "fornecedor": "", "tipo": "", "url": ""},
     "variante": {"id": "v4", "titulo": "Beige / S", "sku": "POT-BG-S",
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
    pagina = render_template_string(CASCA, chave_api=config.CHAVE_API,
                                    T=textos.tabela(g.idioma), idioma=g.idioma)
    # Entra ANTES do script da tela, senão `shopify` ainda não existe na hora
    # em que `comecar()` roda.
    pagina = pagina.replace(
        '<script src="https://cdn.shopify.com/shopifycloud/app-bridge.js"></script>',
        REMENDO)

    cena = request.args.get("cena")
    if cena in CENAS:
        pagina = pagina.replace(
            "</body>",
            "<script>window.__cena = async function(){ %s };</script>%s</body>"
            % (CENAS[cena], AJUDANTES))
    return pagina


# Cenas pras capturas de tela da loja de apps.
#
# Captura tirada clicando na mão não se refaz: quando a tela muda, alguém tem que
# lembrar da sequência exata de cliques, e não lembra. Aqui cada cena é um script
# que monta o estado, então refazer as quatro capturas é rodar um comando.
#
# Não é código de produção: vive só no modo de desenvolvimento, como o resto
# deste arquivo.
CENAS = {
    "principal": """
        marcar(0); marcar(1);
        await esperar(900);
    """,
    "campos": """
        marcar(0);
        campo("fornecedor", true);
        escolher("formato", "avery_5160");
        await esperar(900);
    """,
    # A calibracao fica no fim da coluna da direita: sem rolar, a captura
    # mostrava a tela inteira MENOS justamente o que ela deveria contar.
    "calibracao": """
        marcar(0);
        const cx = document.querySelectorAll("details")[1];
        cx.open = true;
        document.getElementById("dy").value = "-0.5";
        escolher("dx", "1.5");
        await esperar(700);
        // Só a rolagem de DENTRO da coluna: é assim que o lojista chega nesta
        // parte da tela, e a página fica no topo, com o cabeçalho à vista.
        const col = document.querySelector(".direita");
        col.scrollTop = col.scrollHeight;
        await esperar(500);
    """,
    "planos": """
        marcar(0);
        document.getElementById("ver_planos").click();
        await esperar(900);
    """,
}

AJUDANTES = """
<script>
// Os ajudantes ficam em `window` de proposito. A primeira versao declarava eles
// como `const` dentro desta funcao, e o roteiro da cena vive em OUTRO script, no
// escopo global — ele estourava ReferenceError em cima da primeira linha.
//
// O que fez isso demorar pra aparecer nao foi o erro de escopo: foi o `catch`
// logo abaixo, que engolia a excecao e marcava a cena como pronta mesmo assim.
// A captura saia sem produto nenhum selecionado, e o script dizia "ok".
window.esperar = ms => new Promise(r => setTimeout(r, ms));
window.marcar = i => {
  const c = document.querySelectorAll("#lista input[type=checkbox]")[i];
  if (c && !c.checked) c.click();
  if (!c) throw new Error("nao existe produto no indice " + i);
};
window.campo = (nome, ligado) => {
  const c = document.querySelector(".campo[value=" + nome + "]");
  if (!c) throw new Error("nao existe o campo " + nome);
  if (c.checked !== ligado) c.click();
};
window.escolher = (id, v) => {
  const e = document.getElementById(id);
  if (!e) throw new Error("nao existe o controle " + id);
  e.value = v; e.dispatchEvent(new Event("change"));
};

(async function () {
  const cena = new URLSearchParams(location.search).get("cena");
  if (!cena) return;
  const esperar = window.esperar;
  // Espera o catálogo chegar. Contar tempo aqui não funcionava: o Chrome sem
  // janela adianta os temporizadores, então a espera passava num piscar e a
  // cena rodava antes de existir um produto pra marcar.
  if (!document.querySelector("#lista tbody tr")) {
    await new Promise(function (pronto) {
      document.addEventListener("lista-pronta", pronto, {once: true});
    });
  }
  await esperar(300);
  // A falha vai pro DOM, nao só pro console. Quem captura precisa conseguir
  // DISTINGUIR "cena montada" de "cena estourou" — senão a captura sai errada
  // e o script relata sucesso, que foi exatamente o que aconteceu aqui.
  try {
    await window.__cena();
    document.documentElement.setAttribute("data-cena-pronta", "1");
  } catch (e) {
    console.error(e);
    document.documentElement.setAttribute("data-cena-erro", String(e));
  }
})();
</script>
"""


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


PAINEL = """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<title>O que colar no painel do Shopify</title><style>
body{font:14px/1.6 -apple-system,"Segoe UI",system-ui,sans-serif;background:#f1f2f4;
     color:#303030;margin:0;padding:26px}
.cx{background:#fff;border:1px solid #e1e3e5;border-radius:10px;padding:18px;
    max-width:660px;margin:0 0 16px}
h1{font-size:17px;margin:0 0 4px} h2{font-size:13px;margin:0 0 10px}
.sub{color:#616161;font-size:13px;margin:0 0 20px;max-width:660px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;color:#616161;font-weight:600;font-size:11px;padding:0 0 7px;
   text-transform:uppercase;letter-spacing:.03em;width:34%}
td,th{border-bottom:1px solid #f1f2f4;padding:9px 8px 9px 0;vertical-align:top}
code{font:12.5px ui-monospace,Consolas,monospace;background:#f1f2f4;border-radius:5px;
     padding:2px 6px;word-break:break-all;display:inline-block}
.ruim{color:#8e1f0b;background:#fee9e5;border-radius:8px;padding:11px 13px;font-size:13px}
.bom{color:#0c5132;background:#e3f4e9;border-radius:8px;padding:11px 13px;font-size:13px}
ul{margin:8px 0 0;padding-left:20px} li{margin:3px 0}
</style></head><body>
<h1>O que colar no painel do Shopify</h1>
<p class="sub">Gerado a partir do <code>APP_URL</code> que este servidor está usando
agora. O OAuth recusa por um caractere de diferença e não explica o motivo — então
copie daqui, não digite.</p>

{% if not https %}
<div class="cx"><p class="ruim"><strong>O APP_URL ainda é local.</strong>
O Shopify exige https público. Suba o túnel primeiro, ponha a URL dele no
<code>.env</code>, e recarregue esta página.</p></div>
{% else %}
<div class="cx"><p class="bom">APP_URL válido. Os valores abaixo estão prontos.</p></div>
{% endif %}

<div class="cx"><h2>App setup</h2><table>
<tr><th>App URL</th><td><code>{{ url }}</code></td></tr>
<tr><th>Allowed redirection URL(s)</th><td><code>{{ url }}/instalar/volta</code></td></tr>
<tr><th>Embed app in Shopify admin</th><td>ligado</td></tr>
</table></div>

<div class="cx"><h2>Webhooks (Compliance / GDPR)</h2><table>
<tr><th>Customer data request</th><td><code>{{ url }}/webhooks</code></td></tr>
<tr><th>Customer data erasure</th><td><code>{{ url }}/webhooks</code></td></tr>
<tr><th>Shop data erasure</th><td><code>{{ url }}/webhooks</code></td></tr>
</table>
<p class="sub" style="margin:12px 0 0">Os três são obrigatórios pra passar na
revisão, e o Shopify testa. Este app responde honestamente que não guarda dado de
cliente — dá pra conferir nos escopos abaixo.</p></div>

<div class="cx"><h2>Escopos (Access scopes)</h2><table>
<tr><th>Pedidos</th><td><code>read_products, read_inventory</code></td></tr>
</table>
<p class="sub" style="margin:12px 0 0">Só isso. Sem pedido, sem cliente, sem
endereço — cada escopo a mais é uma tela de susto na instalação e uma pergunta
na revisão.</p></div>

<div class="cx"><h2>No seu <code>.env</code></h2><table>
<tr><th>SHOPIFY_CHAVE_API</th><td>o <em>Client ID</em> do painel</td></tr>
<tr><th>SHOPIFY_SEGREDO</th><td>o <em>Client secret</em> — cole direto no arquivo</td></tr>
<tr><th>APP_URL</th><td><code>{{ url }}</code></td></tr>
<tr><th>MODO_DEV</th><td><code>1</code> enquanto testa</td></tr>
</table></div>

<div class="cx"><h2>Depois de mudar o túnel</h2>
<ul>
<li>trocar <code>APP_URL</code> no <code>.env</code></li>
<li>trocar <strong>App URL</strong> e <strong>redirection URL</strong> no painel</li>
<li>reinstalar o app na loja de teste</li>
</ul>
<p class="sub" style="margin:10px 0 0">O endereço do túnel grátis muda a cada vez
que ele sobe. É chato e é o preço de não ter servidor ainda.</p></div>
</body></html>"""


@rotas.get("/shopify")
def painel():
    """Os valores exatos pra colar no painel de Partner.

    Existe porque o OAuth recusa por diferença de um caractere entre a URL
    cadastrada e a que o app manda — e a mensagem não diz isso. Uma barra a mais
    no fim custa uma tarde.
    """
    return render_template_string(
        PAINEL, url=config.URL_DO_APP,
        https=config.URL_DO_APP.startswith("https://"))


# Enchimento pra loja passar de uma página. Um catálogo de 4 itens não exercita
# a paginação, e paginação que nunca rodou é paginação que não funciona — foi
# exatamente assim que a tela ficou meses lendo só os 50 primeiros produtos.
def _enchimento(quantos=118):
    cheio = list(CATALOGO_FALSO)
    for n in range(quantos):
        cheio.append({
            "produto": {"id": "gid://dev/Product/%d" % n,
                        "titulo": "Sample Product %03d" % (n + 1),
                        "fornecedor": "Vendor %d" % (n % 7),
                        "tipo": "Sample", "url": ""},
            "variante": {"id": "vt%d" % n, "titulo": "Default",
                         # Um em cada sete SEM SKU, porque catálogo importado
                         # às pressas é assim — e porque sem isto o gerador de
                         # SKU não tinha o que exercitar no `/dev/`, que é a
                         # única tela testável sem Shopify nenhum.
                         "sku": "" if n % 7 == 3 else "TST-%03d" % (n + 1),
                         # Um em cada cinco sem código, como catálogo de verdade.
                         "codigo_barras": "" if n % 5 == 0 else "789%09d" % n,
                         "preco": "%d.90" % (10 + n % 90), "preco_comparado": "",
                         "estoque": n % 30, "url": ""},
            # Um produto com mais variantes do que a consulta traz, pra exercitar
            # o aviso de corte.
            "variantes_cortadas": n == 3,
        })
    return cheio


TODOS_FALSOS = _enchimento()
POR_PAGINA = 50


def catalogo_falso(busca=None, depois=None):
    """O catálogo de mentira, com busca e paginação por cursor.

    O cursor é só a posição na lista. O do Shopify é opaco e a gente nunca olha
    dentro dele, então imitar com um número é fiel o bastante pro que a tela faz.
    """
    itens = TODOS_FALSOS
    if busca:
        alvo = busca.strip().lower()
        itens = [i for i in itens
                 if alvo in i["produto"]["titulo"].lower()
                 or alvo in (i["variante"]["sku"] or "").lower()
                 or alvo in (i["variante"]["codigo_barras"] or "")]

    inicio = 0
    if depois:
        try:
            inicio = max(0, int(depois))
        except (TypeError, ValueError):
            inicio = 0

    pagina = itens[inicio:inicio + POR_PAGINA]
    fim = inicio + len(pagina)
    return pagina, fim < len(itens), str(fim)


def loja_de_mentira(registro) -> bool:
    """Esta loja é a de desenvolvimento?

    O `MODO_DEV` sozinho não basta: com ele ligado e uma loja de verdade
    instalada, o catálogo falso apareceria no lugar do catálogo dela.
    """
    return bool(config.MODO_DEV) and registro.get("token") == TOKEN_FALSO
