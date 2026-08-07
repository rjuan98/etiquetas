"""As páginas HTML. Por ora, só a casca do app embutido.

A tela de desenhar etiqueta vem depois; o que precisa estar certo agora é o
contrato de entrada, porque é ele que decide se o app abre.

## O que a casca faz

1. confere que a requisição tem uma loja válida
2. se a loja não instalou, escapa do iframe e manda pra instalação
3. carrega o App Bridge, que é quem emite o token de sessão
4. embrulha o `fetch` pra que TODA chamada saia com o token no cabeçalho

O passo 4 é a parte que costuma dar errado. Se cada tela lembrar de pedir o
token e montar o cabeçalho na mão, uma vai esquecer — e essa vai tomar 401 sem
ninguém entender. Embrulhando o `fetch` uma vez, o caminho fácil vira o certo,
que é a mesma ideia do `@exige_loja` do outro lado.
"""
from flask import Blueprint, request, redirect, render_template_string, abort

from loja import dominio
from dados import lojas
from . import config

rotas = Blueprint("tela", __name__)

CASCA = """<!doctype html>
<html lang="pt-BR"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Etiquetas</title>
<meta name="shopify-api-key" content="{{ chave_api }}">
<script src="https://cdn.shopify.com/shopifycloud/app-bridge.js"></script>
<style>
  body { font: 15px/1.5 -apple-system, "Segoe UI", system-ui, sans-serif;
         margin: 0; padding: 2rem; color: #303030; }
  .caixa { max-width: 40rem; }
  h1 { font-size: 1.25rem; margin: 0 0 .5rem; }
  .sumico { color: #616161; }
</style>
</head><body>
<div class="caixa">
  <h1>Etiquetas</h1>
  <p class="sumico" id="estado">Carregando…</p>
</div>
<script>
// Todo pedido à nossa API sai com o token de sessão. Centralizar aqui é o que
// impede uma tela nova de esquecer o cabeçalho e tomar 401 sem motivo aparente.
async function api(caminho, opcoes = {}) {
  const token = await shopify.idToken();
  const cabecalhos = Object.assign({}, opcoes.headers, {
    "Authorization": "Bearer " + token,
  });
  if (opcoes.body && !cabecalhos["Content-Type"]) {
    cabecalhos["Content-Type"] = "application/json";
  }
  return fetch(caminho, Object.assign({}, opcoes, { headers: cabecalhos }));
}
window.api = api;

api("/api/uso")
  .then(r => r.json())
  .then(d => {
    document.getElementById("estado").textContent =
      d.erro ? d.erro
             : `Plano ${d.nome_do_plano} — ${d.etiquetas_no_mes} etiquetas neste mês, ` +
               `${d.modelos} modelo(s).`;
  })
  .catch(() => {
    document.getElementById("estado").textContent =
      "Não consegui falar com o servidor.";
  });
</script>
</body></html>"""

# Mesma página de escape da instalação: um redirect normal tentaria carregar a
# tela do Shopify dentro do iframe, e o Shopify recusa ser embutido.
ESCAPAR = """<!doctype html><meta charset="utf-8">
<script>window.top.location.href = {{ destino|tojson }};</script>
<p style="font:16px system-ui;padding:2rem">
  <a href="{{ destino }}" target="_top">Clique aqui pra instalar o app.</a></p>"""


@rotas.get("/")
def casa():
    loja = request.args.get("shop", "")

    # Sem `shop` é gente chegando pela URL direto, não pelo admin. Não é erro.
    if not loja:
        return render_template_string(
            """<!doctype html><meta charset="utf-8">
            <title>Etiquetas</title>
            <p style="font:16px system-ui;padding:2rem">
              Este app funciona dentro do painel do Shopify.
              Abra pelo admin da sua loja.</p>""")

    if not dominio.valido(loja):
        abort(400, "Domínio de loja inválido.")

    registro = lojas.buscar(loja)
    if not registro or not registro["ativa"]:
        destino = "%s/instalar?shop=%s" % (config.URL_DO_APP,
                                           dominio.normalizar(loja))
        if request.args.get("embedded") == "1":
            return render_template_string(ESCAPAR, destino=destino)
        return redirect(destino)

    return render_template_string(CASCA, chave_api=config.CHAVE_API)
