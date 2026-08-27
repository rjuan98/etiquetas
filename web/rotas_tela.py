"""A tela. Duas colunas: os produtos à esquerda, a etiqueta à direita.

## Por que não tem editor de arrastar

O caminho óbvio pra um app de etiqueta é uma tela onde a pessoa arrasta caixinhas.
É o que parece profissional, e é muito trabalho.

Mas as reclamações que fizeram este projeto existir não pedem isso:

    "não dá pra tirar o campo de preço"        → um interruptor
    "sumiu o SKU da etiqueta"                  → um interruptor
    "o € fica do lado errado"                  → duas opções
    "minha etiqueta sai torta"                 → dois números e uma régua impressa
    "digitar 1 pra cada código, com 2.000"     → a quantidade já vem do estoque

Nenhuma delas é resolvida arrastando caixa. Todas são resolvidas por interruptor
sobre um layout que já nasce bom. Então a primeira versão é isso — e cada opção
aqui existe porque um lojista de verdade reclamou da falta dela.

## Nada de layout é decidido aqui

A tela manda **escolhas** e recebe SVG pronto. O JavaScript não sabe o que é
milímetro, não sabe quebrar texto, não sabe onde o preço fica. Se soubesse,
seria uma segunda implementação da mesma regra — e a prévia começaria a discordar
da impressão, que é o defeito que este app existe pra corrigir.
"""
from flask import Blueprint, request, redirect, render_template_string, abort

from loja import dominio
from dados import lojas
from . import config

rotas = Blueprint("tela", __name__)

# Mesma página de escape da instalação: um redirect normal tentaria carregar a
# tela do Shopify dentro do iframe, e o Shopify recusa ser embutido.
ESCAPAR = """<!doctype html><meta charset="utf-8">
<script>window.top.location.href = {{ destino|tojson }};</script>
<p style="font:16px system-ui;padding:2rem">
  <a href="{{ destino }}" target="_top">Clique aqui pra instalar o app.</a></p>"""

FORA = """<!doctype html><meta charset="utf-8"><title>Etiquetas</title>
<p style="font:16px system-ui;padding:2rem;max-width:32rem;line-height:1.6">
  Este app funciona dentro do painel do Shopify. Abra pelo admin da sua loja.</p>"""

CASCA = r"""<!doctype html>
<html lang="pt-BR"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Etiquetas</title>
<meta name="shopify-api-key" content="{{ chave_api }}">
<script src="https://cdn.shopify.com/shopifycloud/app-bridge.js"></script>
<style>
:root{
  --tinta:#303030; --fraco:#616161; --borda:#e1e3e5; --fundo:#f1f2f4;
  --caixa:#fff; --acento:#303030; --aviso:#8a6116; --aviso-fundo:#fff5ea;
}
*{box-sizing:border-box}
body{margin:0;background:var(--fundo);color:var(--tinta);
     font:14px/1.5 -apple-system,"Segoe UI",system-ui,sans-serif}
.topo{display:flex;align-items:center;justify-content:space-between;gap:12px;
      padding:14px 20px;background:var(--caixa);border-bottom:1px solid var(--borda)}
.topo h1{font-size:15px;margin:0;font-weight:650}
.plano{font-size:12px;color:var(--fraco)}
.grade{display:grid;grid-template-columns:1fr 340px;gap:16px;padding:16px;
       align-items:start;max-width:1180px;margin:0 auto}
@media(max-width:900px){.grade{grid-template-columns:1fr}}
.cx{background:var(--caixa);border:1px solid var(--borda);border-radius:10px;padding:14px}
.cx h2{font-size:13px;margin:0 0 10px;font-weight:650}
.direita{position:sticky;top:16px;display:flex;flex-direction:column;gap:16px}
label{display:block;font-size:12px;color:var(--fraco);margin:0 0 4px}
input[type=text],input[type=number],input[type=search],select{
  width:100%;padding:7px 9px;border:1px solid #8a8a8a;border-radius:7px;
  font:inherit;font-size:13px;background:#fff;color:var(--tinta)}
input:focus,select:focus{outline:2px solid #005bd3;outline-offset:0;border-color:#005bd3}
.b{display:inline-flex;align-items:center;justify-content:center;gap:6px;
   padding:8px 13px;border-radius:8px;border:1px solid #8a8a8a;background:#fff;
   font:inherit;font-size:13px;font-weight:600;cursor:pointer;color:var(--tinta)}
.b:hover{background:#f7f7f7}
.b.forte{background:var(--acento);color:#fff;border-color:var(--acento)}
.b.forte:hover{background:#1a1a1a}
.b:disabled{opacity:.5;cursor:not-allowed}
.b:focus-visible{outline:2px solid #005bd3;outline-offset:2px}
.previa{background:
  linear-gradient(45deg,#eceef0 25%,transparent 25%,transparent 75%,#eceef0 75%),
  linear-gradient(45deg,#eceef0 25%,transparent 25%,transparent 75%,#eceef0 75%);
  background-size:14px 14px;background-position:0 0,7px 7px;
  border:1px solid var(--borda);border-radius:8px;padding:16px;display:flex;
  justify-content:center;align-items:center;min-height:120px}
.previa svg{filter:drop-shadow(0 1px 4px rgba(0,0,0,.2));max-width:100%}
.medida{font-size:11.5px;color:var(--fraco);text-align:center;margin:7px 0 0}
.aviso{font-size:12px;color:var(--aviso);background:var(--aviso-fundo);
       border-radius:7px;padding:7px 9px;margin:10px 0 0}
.erro{font-size:12px;color:#8e1f0b;background:#fee9e5;border-radius:7px;
      padding:7px 9px;margin:10px 0 0}
.campos{display:grid;gap:5px;margin:0 0 12px}
.campos label{display:flex;align-items:center;gap:8px;font-size:13px;
              color:var(--tinta);margin:0;cursor:pointer;padding:2px 0}
.par{display:grid;grid-template-columns:1fr 1fr;gap:9px}
.linha{display:flex;gap:8px;align-items:center}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;font-size:11px;color:var(--fraco);font-weight:600;
   padding:0 8px 7px;border-bottom:1px solid var(--borda);text-transform:uppercase;
   letter-spacing:.03em}
td{padding:8px;border-bottom:1px solid #f1f2f4;vertical-align:middle}
td.q{width:78px} td.c{width:30px}
.t{font-weight:550} .s{font-size:11.5px;color:var(--fraco)}
.vazio{color:var(--fraco);font-size:13px;padding:22px 4px;text-align:center}
.barra{position:sticky;bottom:0;background:var(--caixa);border-top:1px solid var(--borda);
       padding:11px 16px;display:flex;gap:10px;align-items:center;justify-content:flex-end;
       flex-wrap:wrap}
.conta{margin-right:auto;font-size:13px;color:var(--fraco)}
details{margin:12px 0 0;border-top:1px solid var(--borda);padding:11px 0 0}
summary{font-size:12.5px;font-weight:600;cursor:pointer;color:var(--tinta)}
summary:focus-visible{outline:2px solid #005bd3}
.ajuda{font-size:11.5px;color:var(--fraco);margin:7px 0 9px;line-height:1.45}
.oculto{display:none}
</style>
</head><body>

<div class="topo">
  <h1>Etiquetas</h1>
  <span class="plano" id="plano">carregando…</span>
</div>

<div class="grade">
  <div>
    <div class="cx">
      <h2>Produtos</h2>
      <div class="linha" style="margin:0 0 12px">
        <input type="search" id="busca" placeholder="Buscar por nome, SKU ou código">
        <button class="b" id="buscar">Buscar</button>
      </div>
      <div id="lista"><p class="vazio">Carregando o catálogo…</p></div>
    </div>
  </div>

  <div class="direita">
    <div class="cx">
      <h2>A etiqueta</h2>
      <div class="previa" id="previa"><span class="s">montando…</span></div>
      <p class="medida" id="medida"></p>
      <div id="recado"></div>
    </div>

    <div class="cx">
      <h2>O que aparece</h2>
      <div class="campos" id="campos"></div>

      <label for="formato">Formato do papel</label>
      <select id="formato"></select>

      <details>
        <summary>Preço e código</summary>
        <div class="par" style="margin:10px 0 0">
          <div>
            <label for="simbolo">Símbolo</label>
            <input type="text" id="simbolo" value="R$" maxlength="4">
          </div>
          <div>
            <label for="posicao">Posição</label>
            <select id="posicao">
              <option value="antes">R$ 24,90</option>
              <option value="depois">24,90 €</option>
            </select>
          </div>
          <div>
            <label for="decimal">Decimal</label>
            <select id="decimal">
              <option value=",">24,90</option>
              <option value=".">24.90</option>
            </select>
          </div>
          <div>
            <label for="simbologia">Tipo de código</label>
            <select id="simbologia">
              <option value="EAN13">EAN-13</option>
              <option value="UPCA">UPC-A</option>
              <option value="CODE128">Code 128</option>
              <option value="QRCODE">QR Code</option>
            </select>
          </div>
        </div>
        <label style="display:flex;align-items:center;gap:8px;margin:11px 0 0;
                      font-size:13px;color:var(--tinta);cursor:pointer">
          <input type="checkbox" id="rotulo_sku" checked> Escrever "SKU:" antes do código
        </label>
      </details>

      <details>
        <summary>A etiqueta está saindo torta?</summary>
        <p class="ajuda">Imprima a régua em <strong>tamanho real (100%)</strong>,
          meça com régua de verdade onde a moldura caiu, e escreva a diferença.
          Vale pra qualquer impressora.</p>
        <div class="par">
          <div>
            <label for="dx">Desviar na horizontal (mm)</label>
            <input type="number" id="dx" value="0" step="0.5">
          </div>
          <div>
            <label for="dy">Desviar na vertical (mm)</label>
            <input type="number" id="dy" value="0" step="0.5">
          </div>
        </div>
        <button class="b" id="regua" style="margin:10px 0 0">Baixar a régua</button>
      </details>
    </div>
  </div>
</div>

<div class="barra">
  <span class="conta" id="conta">nenhum produto escolhido</span>
  <button class="b" id="zpl">Impressora térmica (ZPL)</button>
  <button class="b forte" id="pdf">Baixar PDF</button>
</div>

<script>
"use strict";

// Todo pedido sai com o token de sessão. Centralizar aqui é o que impede uma
// tela nova de esquecer o cabeçalho e tomar 401 sem motivo aparente.
async function api(caminho, opcoes) {
  opcoes = opcoes || {};
  const token = await shopify.idToken();
  const cab = Object.assign({}, opcoes.headers, {Authorization: "Bearer " + token});
  if (opcoes.body && !cab["Content-Type"]) cab["Content-Type"] = "application/json";
  return fetch(caminho, Object.assign({}, opcoes, {headers: cab}));
}

const $ = function (id) { return document.getElementById(id); };
const itens = [];                       // o catálogo carregado
const escolhidos = new Map();           // id da variante → quantidade

// A receita é só ESCOLHA. Nenhuma coordenada, nenhum milímetro: quem traduz
// isso em etiqueta é o servidor, pelo mesmo caminho que imprime.
function receita() {
  return {
    formato: $("formato").value,
    campos: Array.from(document.querySelectorAll(".campo:checked"))
                 .map(function (c) { return c.value; }),
    simbolo: $("simbolo").value,
    simbolo_depois: $("posicao").value === "depois",
    separador_decimal: $("decimal").value,
    separador_milhar: $("decimal").value === "," ? "." : ",",
    rotulo_sku: $("rotulo_sku").checked,
    simbologia: $("simbologia").value,
    desvio_x_mm: parseFloat($("dx").value) || 0,
    desvio_y_mm: parseFloat($("dy").value) || 0
  };
}

function primeiroEscolhido() {
  for (const it of itens) {
    if (escolhidos.has(it.variante.id)) return it;
  }
  return null;
}

// A prévia é do produto escolhido, não de um exemplo genérico: é assim que a
// pessoa vê que o título dela é longo demais ANTES de imprimir duzentas.
let pedido = 0;
async function atualizarPrevia() {
  const meu = ++pedido;
  const corpo = {receita: receita()};
  const it = primeiroEscolhido();
  if (it) corpo.item = it;

  const r = await api("/api/previa", {method: "POST", body: JSON.stringify(corpo)});
  const d = await r.json();
  if (meu !== pedido) return;           // resposta velha chegou atrasada

  if (!r.ok) { $("recado").innerHTML = '<p class="erro"></p>';
               $("recado").firstChild.textContent = d.erro || "Erro na prévia."; return; }

  $("previa").innerHTML = d.svg;
  $("medida").textContent = d.largura_mm + " × " + d.altura_mm + " mm";
  if (d.nao_coube && d.nao_coube.length) {
    const nomes = d.nao_coube.map(function (c) { return nomeDoCampo(c); }).join(", ");
    $("recado").innerHTML = '<p class="aviso"></p>';
    $("recado").firstChild.textContent =
      "Não coube nesta etiqueta: " + nomes + ". Escolha um papel maior ou desligue algum campo.";
  } else {
    $("recado").innerHTML = "";
  }
}

let CAMPOS = [];
function nomeDoCampo(chave) {
  const c = CAMPOS.find(function (x) { return x.chave === chave; });
  return c ? c.nome.toLowerCase() : chave;
}

function contar() {
  let total = 0;
  escolhidos.forEach(function (q) { total += q; });
  $("conta").textContent = escolhidos.size === 0
    ? "nenhum produto escolhido"
    : escolhidos.size + " produto(s), " + total + " etiqueta(s)";
  $("pdf").disabled = $("zpl").disabled = escolhidos.size === 0;
}

function desenharLista() {
  if (!itens.length) {
    $("lista").innerHTML = '<p class="vazio">Nenhum produto encontrado.</p>';
    return;
  }
  const tabela = document.createElement("table");
  tabela.innerHTML =
    "<thead><tr><th class=c></th><th>Produto</th><th>Código</th>" +
    "<th class=q>Quantas</th></tr></thead>";
  const corpo = document.createElement("tbody");

  itens.forEach(function (it) {
    const id = it.variante.id;
    const tr = document.createElement("tr");

    const tdC = document.createElement("td");
    const marca = document.createElement("input");
    marca.type = "checkbox";
    marca.checked = escolhidos.has(id);
    marca.setAttribute("aria-label", "Escolher " + it.produto.titulo);
    tdC.appendChild(marca);

    const tdN = document.createElement("td");
    const t = document.createElement("div"); t.className = "t";
    t.textContent = it.produto.titulo;
    const s = document.createElement("div"); s.className = "s";
    s.textContent = [it.variante.titulo, it.variante.sku && ("SKU " + it.variante.sku)]
                    .filter(Boolean).join(" · ");
    tdN.appendChild(t); tdN.appendChild(s);

    const tdB = document.createElement("td"); tdB.className = "s";
    // Produto sem código de barras não sai etiqueta com código — dizer isso aqui
    // é melhor que a pessoa descobrir olhando o papel em branco.
    tdB.textContent = it.variante.codigo_barras || "sem código";

    const tdQ = document.createElement("td"); tdQ.className = "q";
    const q = document.createElement("input");
    q.type = "number"; q.min = "1"; q.value = escolhidos.get(id) || it.quantidade || 1;
    q.setAttribute("aria-label", "Quantas etiquetas de " + it.produto.titulo);
    tdQ.appendChild(q);

    marca.addEventListener("change", function () {
      if (marca.checked) escolhidos.set(id, parseInt(q.value, 10) || 1);
      else escolhidos.delete(id);
      contar(); atualizarPrevia();
    });
    q.addEventListener("change", function () {
      if (escolhidos.has(id)) escolhidos.set(id, Math.max(1, parseInt(q.value, 10) || 1));
      contar();
    });

    tr.appendChild(tdC); tr.appendChild(tdN); tr.appendChild(tdB); tr.appendChild(tdQ);
    corpo.appendChild(tr);
  });

  tabela.appendChild(corpo);
  $("lista").innerHTML = "";
  $("lista").appendChild(tabela);
}

async function carregarProdutos(busca) {
  $("lista").innerHTML = '<p class="vazio">Carregando…</p>';
  const url = "/api/produtos?quantos=50" + (busca ? "&busca=" + encodeURIComponent(busca) : "");
  const r = await api(url);
  const d = await r.json();
  itens.length = 0;
  if (!r.ok) {
    $("lista").innerHTML = '<p class="vazio"></p>';
    $("lista").firstChild.textContent = d.erro || "Não consegui ler o catálogo.";
    return;
  }
  (d.itens || []).forEach(function (i) { itens.push(i); });
  desenharLista();
}

function fila() {
  const saida = [];
  itens.forEach(function (it) {
    if (escolhidos.has(it.variante.id)) {
      saida.push(Object.assign({}, it, {quantidade: escolhidos.get(it.variante.id)}));
    }
  });
  return saida;
}

async function baixar(caminho, corpo, arquivo) {
  const r = await api(caminho, {method: "POST", body: JSON.stringify(corpo)});
  if (!r.ok) {
    let m = "Não consegui gerar o arquivo.";
    try { m = (await r.json()).erro || m; } catch (e) {}
    $("recado").innerHTML = '<p class="erro"></p>';
    $("recado").firstChild.textContent = m;
    return;
  }
  const blob = await r.blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = arquivo;
  document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(a.href);
  carregarUso();
}

async function carregarUso() {
  const r = await api("/api/uso");
  const d = await r.json();
  if (!r.ok) { $("plano").textContent = d.erro || ""; return; }
  $("plano").textContent = d.limite_mes
    ? "Plano " + d.nome_do_plano + " — " + d.etiquetas_no_mes + " de " +
      d.limite_mes + " etiquetas neste mês"
    : "Plano " + d.nome_do_plano;
  // Térmica é do plano pago. Deixar o botão clicável pra tomar 402 depois seria
  // prometer o que não entrega.
  $("zpl").title = d.motores.indexOf("zpl") < 0
    ? "A impressora térmica faz parte do plano Pro" : "";
}

async function comecar() {
  const r = await api("/api/formatos");
  const d = await r.json();
  CAMPOS = d.campos || [];

  $("formato").innerHTML = "";
  (d.formatos || []).forEach(function (f) {
    const o = document.createElement("option");
    o.value = f.codigo;
    o.textContent = f.nome + " — " + f.largura_mm + "×" + f.altura_mm + "mm" +
                    (f.por_folha ? " (" + f.por_folha + " por folha)" : "");
    $("formato").appendChild(o);
  });

  const marcados = d.padrao || [];
  $("campos").innerHTML = "";
  CAMPOS.forEach(function (c) {
    const l = document.createElement("label");
    const i = document.createElement("input");
    i.type = "checkbox"; i.className = "campo"; i.value = c.chave;
    i.checked = marcados.indexOf(c.chave) >= 0;
    i.addEventListener("change", atualizarPrevia);
    l.appendChild(i);
    l.appendChild(document.createTextNode(" " + c.nome));
    $("campos").appendChild(l);
  });

  ["formato", "simbolo", "posicao", "decimal", "simbologia", "rotulo_sku", "dx", "dy"]
    .forEach(function (id) { $(id).addEventListener("change", atualizarPrevia); });

  $("buscar").addEventListener("click", function () { carregarProdutos($("busca").value); });
  $("busca").addEventListener("keydown", function (e) {
    if (e.key === "Enter") carregarProdutos($("busca").value);
  });
  $("pdf").addEventListener("click", function () {
    baixar("/api/imprimir", {motor: "pdf", receita: receita(), itens: fila()},
           "etiquetas.pdf");
  });
  $("zpl").addEventListener("click", function () {
    baixar("/api/imprimir", {motor: "zpl", receita: receita(), itens: fila()},
           "etiquetas.zpl");
  });
  $("regua").addEventListener("click", function () {
    baixar("/api/calibracao.pdf", {receita: receita()}, "regua-de-calibracao.pdf");
  });

  contar();
  atualizarPrevia();
  carregarUso();
  carregarProdutos("");
}

comecar().catch(function () {
  $("plano").textContent = "Não consegui falar com o servidor.";
});
</script>
</body></html>"""


@rotas.get("/")
def casa():
    loja = request.args.get("shop", "")

    # Sem `shop` é gente chegando pela URL direto, não pelo admin. Não é erro.
    if not loja:
        return render_template_string(FORA)

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
