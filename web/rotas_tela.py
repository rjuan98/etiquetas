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
from flask import (Blueprint, request, redirect, render_template_string,
                   abort, g)

from loja import dominio
from dados import lojas
from . import config, textos

rotas = Blueprint("tela", __name__)

# Mesma página de escape da instalação: um redirect normal tentaria carregar a
# tela do Shopify dentro do iframe, e o Shopify recusa ser embutido.
ESCAPAR = """<!doctype html><meta charset="utf-8">
<script>window.top.location.href = {{ destino|tojson }};</script>
<p style="font:16px system-ui;padding:2rem">
  <a href="{{ destino }}" target="_top">{{ T.instalar_aqui }}</a></p>"""

FORA = """<!doctype html><meta charset="utf-8"><title>{{ T.app_titulo }}</title>
<p style="font:16px system-ui;padding:2rem;max-width:32rem;line-height:1.6">
  {{ T.fora_do_admin }}</p>"""

CASCA = r"""<!doctype html>
<html lang="{{ idioma }}"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ T.app_titulo }}</title>
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
dialog{border:1px solid var(--borda);border-radius:12px;padding:20px;max-width:32rem;
       width:calc(100% - 32px);color:var(--tinta);background:var(--caixa)}
dialog::backdrop{background:rgba(0,0,0,.42)}
dialog h2{font-size:15px;margin:0 0 4px;font-weight:650}
.pl{border:1px solid var(--borda);border-radius:9px;padding:12px;margin:10px 0 0;
    display:flex;gap:12px;align-items:flex-start}
.pl.atual{border-color:var(--tinta);background:#fafafa}
.pl .txt{flex:1}
.pl .nm{font-weight:650;font-size:13.5px}
.pl .rs{font-size:12px;color:var(--fraco);margin:2px 0 0}
.pl .pr{font-size:13px;font-weight:650;white-space:nowrap}
.selo{font-size:11px;font-weight:650;color:#0c5132;background:#e3f4e9;
      border-radius:20px;padding:2px 9px;white-space:nowrap}
</style>
</head><body>

<div class="topo">
  <h1>{{ T.app_titulo }}</h1>
  <div class="linha">
    <span class="plano" id="plano">{{ T.carregando }}</span>
    <button class="b" id="ver_planos">{{ T.ver_planos }}</button>
  </div>
</div>

<dialog id="dlg_planos">
  <h2>{{ T.planos }}</h2>
  <p class="ajuda" id="teste_gratis"></p>
  <div id="lista_planos"></div>
  <div class="linha" style="justify-content:flex-end;margin:14px 0 0">
    <button class="b" id="fechar_planos">{{ T.fechar }}</button>
  </div>
  <p class="ajuda" id="aviso_teste" style="margin:12px 0 0"></p>
</dialog>

<div class="grade">
  <div>
    <div class="cx">
      <h2>{{ T.produtos }}</h2>
      <div class="linha" style="margin:0 0 12px">
        <input type="search" id="busca" placeholder="{{ T.buscar_dica }}">
        <button class="b" id="buscar">{{ T.buscar }}</button>
      </div>
      <div id="lista"><p class="vazio">{{ T.carregando_catalogo }}</p></div>
      <div id="aviso_catalogo"></div>
      <div class="linha" style="justify-content:center;margin:12px 0 0">
        <button class="b oculto" id="mais">{{ T.carregar_mais }}</button>
      </div>
    </div>
  </div>

  <div class="direita">
    <div class="cx">
      <h2>{{ T.a_etiqueta }}</h2>
      <div class="previa" id="previa"><span class="s">{{ T.montando }}</span></div>
      <p class="medida" id="medida"></p>
      <div id="recado"></div>
    </div>

    <div class="cx">
      <h2>{{ T.modelo }}</h2>
      <label for="modelo">{{ T.modelo_salvo }}</label>
      <select id="modelo"></select>
      <div style="margin:10px 0 0">
        <label for="nome">{{ T.nome }}</label>
        <input type="text" id="nome" placeholder="{{ T.nome_dica }}" maxlength="60">
      </div>
      <div class="linha" style="margin:10px 0 0;flex-wrap:wrap">
        <button class="b forte" id="salvar">{{ T.salvar }}</button>
        <button class="b" id="duplicar">{{ T.duplicar }}</button>
        <button class="b" id="apagar">{{ T.apagar }}</button>
      </div>
      <p class="ajuda" id="estado_modelo" style="margin:9px 0 0"></p>
    </div>

    <div class="cx">
      <h2>{{ T.o_que_aparece }}</h2>
      <div class="campos" id="campos"></div>

      <label for="formato">{{ T.formato_do_papel }}</label>
      <select id="formato"></select>

      <details>
        <summary>{{ T.preco_e_codigo }}</summary>
        <div class="par" style="margin:10px 0 0">
          <div>
            <label for="simbolo">{{ T.simbolo }}</label>
            <input type="text" id="simbolo" value="R$" maxlength="4">
          </div>
          <div>
            <label for="posicao">{{ T.posicao }}</label>
            <select id="posicao">
              <option value="antes">R$ 24,90</option>
              <option value="depois">24,90 €</option>
            </select>
          </div>
          <div>
            <label for="decimal">{{ T.decimal }}</label>
            <select id="decimal">
              <option value=",">24,90</option>
              <option value=".">24.90</option>
            </select>
          </div>
          <div>
            <label for="simbologia">{{ T.tipo_de_codigo }}</label>
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
          <input type="checkbox" id="rotulo_sku" checked> {{ T.rotulo_sku }}
        </label>
      </details>

      <details>
        <summary>{{ T.sai_torta }}</summary>
        <p class="ajuda">{{ T.regua_ajuda|safe }}</p>
        <div class="par">
          <div>
            <label for="dx">{{ T.desvio_x }}</label>
            <input type="number" id="dx" value="0" step="0.5">
          </div>
          <div>
            <label for="dy">{{ T.desvio_y }}</label>
            <input type="number" id="dy" value="0" step="0.5">
          </div>
        </div>
        <button class="b" id="regua" style="margin:10px 0 0">{{ T.baixar_regua }}</button>
      </details>
    </div>
  </div>
</div>

<div class="barra">
  <span class="conta" id="conta">{{ T.nenhum_escolhido }}</span>
  <button class="b" id="zpl">{{ T.termica }}</button>
  <button class="b forte" id="pdf">{{ T.baixar_pdf }}</button>
</div>

<script>
"use strict";

// Os textos vêm prontos do servidor. O JavaScript não guarda frase nenhuma:
// se guardasse, seriam duas tabelas pra manter e uma delas ficaria pra trás.
const T = {{ T|tojson }};
const IDIOMA = {{ idioma|tojson }};

// Todo pedido sai com o token de sessão. Centralizar aqui é o que impede uma
// tela nova de esquecer o cabeçalho e tomar 401 sem motivo aparente.
async function api(caminho, opcoes) {
  opcoes = opcoes || {};
  // O idioma vai junto: sem isso as mensagens de erro da API voltariam sempre
  // no padrão, enquanto a tela ao redor está na língua do lojista.
  caminho += (caminho.indexOf("?") < 0 ? "?" : "&") + "idioma=" + IDIOMA;
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

// ------------------------------------------------------------------ modelos
// `salvo` é a receita como ela está no banco. Comparar com a atual é o que
// permite dizer "tem alteração não salva" — sem isso a pessoa mexe em tudo,
// fecha a aba e perde o trabalho achando que estava guardado.
let modeloAtual = null;      // id do modelo aberto, ou null pra "novo"
let salvo = null;            // JSON da receita como está no banco
let limiteModelos = 0;       // 0 = sem limite
let quantosModelos = 0;

function aplicarReceita(r) {
  const set = function (id, v) { if (v !== undefined) $(id).value = v; };
  set("formato", r.formato);
  set("simbolo", r.simbolo);
  set("posicao", r.simbolo_depois ? "depois" : "antes");
  set("decimal", r.separador_decimal);
  set("simbologia", r.simbologia);
  set("dx", r.desvio_x_mm);
  set("dy", r.desvio_y_mm);
  $("rotulo_sku").checked = r.rotulo_sku !== false;
  const ligados = r.campos || [];
  document.querySelectorAll(".campo").forEach(function (c) {
    c.checked = ligados.indexOf(c.value) >= 0;
  });
}

function marcarEstado() {
  const mudou = salvo !== null && salvo !== JSON.stringify(receita());
  const p = $("estado_modelo");
  if (modeloAtual === null) {
    p.textContent = limiteModelos && quantosModelos >= limiteModelos
      ? T.limite_de_modelos_aviso.replace("%d", limiteModelos)
      : T.ainda_nao_salvo;
  } else {
    p.textContent = mudou ? T.alteracao_nao_salva : T.salvo;
  }
  $("apagar").disabled = $("duplicar").disabled = modeloAtual === null;
  $("apagar").textContent = T.apagar;
}

async function carregarModelos(selecionar) {
  const r = await api("/api/modelos");
  const d = await r.json();
  const lista = (d.modelos || []);
  quantosModelos = lista.length;

  $("modelo").innerHTML = "";
  const novo = document.createElement("option");
  novo.value = ""; novo.textContent = T.novo_modelo;
  $("modelo").appendChild(novo);
  lista.forEach(function (m) {
    const o = document.createElement("option");
    o.value = String(m.id); o.textContent = m.nome;
    $("modelo").appendChild(o);
  });
  $("modelo").value = selecionar === undefined || selecionar === null
    ? (modeloAtual === null ? "" : String(modeloAtual))
    : String(selecionar);
  marcarEstado();
}

async function abrirModelo(id) {
  if (!id) {
    modeloAtual = null; salvo = null; $("nome").value = "";
    marcarEstado(); atualizarPrevia(); return;
  }
  const r = await api("/api/modelos/" + id);
  const d = await r.json();
  if (!r.ok) { avisar(d.erro || T.erro_abrir_modelo); return; }
  modeloAtual = d.id;
  $("nome").value = d.nome || "";
  // A receita é o que devolve os botões ao estado em que foram salvos. Sem ela
  // o modelo abriria com tudo no padrão, sem relação com a etiqueta na tela.
  if (d.receita && Object.keys(d.receita).length) aplicarReceita(d.receita);
  salvo = JSON.stringify(receita());
  marcarEstado();
  atualizarPrevia();
}

function avisar(texto, tipo) {
  $("recado").innerHTML = '<p class="' + (tipo || "erro") + '"></p>';
  $("recado").firstChild.textContent = texto;
}

// Motivos em que o app está recusando por causa do PLANO, não por erro. Aqui a
// resposta certa não é só dizer não: é mostrar a saída. Recusar sem oferecer
// caminho é onde o lojista fecha a aba.
const MOTIVOS_DE_PLANO = ["limite_do_mes", "limite_de_modelos", "motor_bloqueado"];

function avisarSobrePlano(texto, motivo) {
  avisar(texto, "aviso");
  if (MOTIVOS_DE_PLANO.indexOf(motivo) < 0) return;
  const b = document.createElement("button");
  b.className = "b forte";
  b.style.margin = "9px 0 0";
  b.textContent = "Ver planos";
  b.addEventListener("click", abrirPlanos);
  $("recado").appendChild(b);
}

// Enquanto uma operação está no ar, os botões que mexem em modelo ficam
// travados. Sem isto, dois cliques em Salvar criam dois modelos, e apagar
// durante um duplicar apaga o registro errado — foi o que aconteceu num teste:
// cliquei em apagar e o modelo continuou lá, porque a lista ainda estava sendo
// recarregada por trás.
const BOTOES = ["salvar", "duplicar", "apagar", "pdf", "zpl", "regua"];
let ocupado = false;

async function comTrava(tarefa) {
  if (ocupado) return;
  ocupado = true;
  BOTOES.forEach(function (id) { $(id).disabled = true; });
  try {
    await tarefa();
  } catch (e) {
    avisar(T.erro_generico);
  } finally {
    ocupado = false;
    BOTOES.forEach(function (id) { $(id).disabled = false; });
    marcarEstado();   // devolve apagar/duplicar ao estado certo
    contar();         // devolve pdf/zpl ao estado certo
  }
}

async function guardar() {
  const corpo = {nome: $("nome").value || "Sem nome", receita: receita()};
  const novo = modeloAtual === null;
  const r = await api(novo ? "/api/modelos" : "/api/modelos/" + modeloAtual,
                      {method: novo ? "POST" : "PUT", body: JSON.stringify(corpo)});
  const d = await r.json();
  if (!r.ok) {
    if (d.motivo === "limite_de_modelos") avisarSobrePlano(d.erro, d.motivo);
    else avisar(d.erro || T.erro_salvar);
    return;
  }
  if (novo) modeloAtual = d.id;
  salvo = JSON.stringify(receita());
  $("recado").innerHTML = "";
  await carregarModelos(modeloAtual);
}

// Mexer num controle não dispara a prévia na hora. Quem mexe numa opção
// costuma mexer em três seguidas, e sem isto cada uma vira uma ida ao servidor
// — as respostas se enfileiram e o resto do app espera atrás delas. Deu pra
// medir: o botão Salvar levou 1,2s pra responder porque estava na fila.
//
// 250ms é curto o bastante pra parecer imediato e longo o bastante pra juntar
// uma rajada de cliques numa requisição só.
let temporizador = null;
function pedirPrevia() {
  clearTimeout(temporizador);
  temporizador = setTimeout(atualizarPrevia, 250);
}

function mudou() {
  pedirPrevia();
  marcarEstado();      // esse é local e instantâneo: não espera o servidor
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
               $("recado").firstChild.textContent = d.erro || T.erro_previa; return; }

  $("previa").innerHTML = d.svg;
  $("medida").textContent = d.largura_mm + " × " + d.altura_mm + " mm";
  if (d.nao_coube && d.nao_coube.length) {
    const nomes = d.nao_coube.map(function (c) { return nomeDoCampo(c); }).join(", ");
    $("recado").innerHTML = '<p class="aviso"></p>';
    $("recado").firstChild.textContent =
      T.nao_coube.replace("%s", nomes);
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
    ? T.nenhum_escolhido
    : T.conta_escolhidos.replace("%d", escolhidos.size).replace("%d", total);
  $("pdf").disabled = $("zpl").disabled = escolhidos.size === 0;
}

function desenharLista() {
  if (!itens.length) {
    $("lista").innerHTML = '<p class="vazio"></p>';
    $("lista").firstChild.textContent = T.nenhum_produto;
    return;
  }
  const tabela = document.createElement("table");
  tabela.innerHTML =
    "<thead><tr><th class=c></th><th>" + T.col_produto + "</th><th>" +
    T.col_codigo + "</th><th class=q>" + T.col_quantas + "</th></tr></thead>";
  const corpo = document.createElement("tbody");

  itens.forEach(function (it) {
    const id = it.variante.id;
    const tr = document.createElement("tr");

    const tdC = document.createElement("td");
    const marca = document.createElement("input");
    marca.type = "checkbox";
    marca.checked = escolhidos.has(id);
    marca.setAttribute("aria-label", T.escolher.replace("%s", it.produto.titulo));
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
    tdB.textContent = it.variante.codigo_barras || T.sem_codigo;

    const tdQ = document.createElement("td"); tdQ.className = "q";
    const q = document.createElement("input");
    q.type = "number"; q.min = "1"; q.value = escolhidos.get(id) || it.quantidade || 1;
    q.setAttribute("aria-label", T.quantas_de.replace("%s", it.produto.titulo));
    tdQ.appendChild(q);

    marca.addEventListener("change", function () {
      if (marca.checked) escolhidos.set(id, parseInt(q.value, 10) || 1);
      else escolhidos.delete(id);
      contar(); pedirPrevia();
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

// O catálogo vem de 50 em 50. A primeira versão pedia a primeira página e
// ignorava o cursor que a API devolvia — numa loja com 200 produtos, os 150 de
// baixo simplesmente não existiam, e nada na tela dizia isso.
let buscaAtual = "";
let cursorAtual = null;

async function carregarProdutos(busca, continuar) {
  if (!continuar) {
    buscaAtual = busca || "";
    cursorAtual = null;
    itens.length = 0;
    $("lista").innerHTML = '<p class="vazio"></p>';
    $("lista").firstChild.textContent = T.carregando;
    $("aviso_catalogo").innerHTML = "";
  }
  $("mais").disabled = true;

  let url = "/api/produtos?quantos=50";
  if (buscaAtual) url += "&busca=" + encodeURIComponent(buscaAtual);
  if (continuar && cursorAtual) url += "&depois=" + encodeURIComponent(cursorAtual);

  const r = await api(url);
  const d = await r.json();
  $("mais").disabled = false;

  if (!r.ok) {
    $("lista").innerHTML = '<p class="vazio"></p>';
    $("lista").firstChild.textContent = d.erro || T.erro_catalogo;
    $("mais").classList.add("oculto");
    return;
  }

  (d.itens || []).forEach(function (i) { itens.push(i); });
  cursorAtual = d.cursor || null;
  $("mais").classList.toggle("oculto", !d.tem_mais);

  // Produto com mais de 100 variantes vem cortado pela consulta. Sumir em
  // silêncio faria o lojista imprimir a prateleira faltando tamanhos.
  if (d.variantes_cortadas && d.variantes_cortadas.length) {
    $("aviso_catalogo").innerHTML = '<p class="aviso"></p>';
    $("aviso_catalogo").firstChild.textContent =
      T.variantes_cortadas.replace("%s", d.variantes_cortadas.join(", "));
  }
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
    let m = T.erro_arquivo, motivo = "";
    try { const d = await r.json(); m = d.erro || m; motivo = d.motivo || ""; }
    catch (e) {}
    avisarSobrePlano(m, motivo);
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

// ----------------------------------------------------------------- cobrança

async function abrirPlanos() {
  const r = await api("/api/planos");
  const d = await r.json();
  if (!r.ok) { avisar(d.erro || T.erro_planos); return; }

  $("teste_gratis").textContent = d.dias_de_teste
    ? T.teste_gratis.replace("%d", d.dias_de_teste)
    : "";

  const caixa = $("lista_planos");
  caixa.innerHTML = "";
  (d.planos || []).forEach(function (p) {
    const linha = document.createElement("div");
    linha.className = "pl" + (p.codigo === d.atual ? " atual" : "");

    const txt = document.createElement("div"); txt.className = "txt";
    const nm = document.createElement("div"); nm.className = "nm";
    nm.textContent = p.nome;
    const rs = document.createElement("div"); rs.className = "rs";
    rs.textContent = p.resumo;
    txt.appendChild(nm); txt.appendChild(rs);

    const dir = document.createElement("div");
    if (p.codigo === d.atual) {
      const selo = document.createElement("span");
      selo.className = "selo"; selo.textContent = T.seu_plano;
      dir.appendChild(selo);
    } else if (p.preco_usd > 0) {
      const b = document.createElement("button");
      b.className = "b forte";
      b.textContent = T.por_mes.replace("%s", p.preco_usd.toFixed(2));
      b.addEventListener("click", function () { assinar(p.codigo, b); });
      dir.appendChild(b);
    } else {
      const pr = document.createElement("span");
      pr.className = "pr"; pr.textContent = T.gratis_minusculo;
      dir.appendChild(pr);
    }

    linha.appendChild(txt); linha.appendChild(dir);
    caixa.appendChild(linha);
  });

  $("dlg_planos").showModal();
}

async function assinar(codigo, botao) {
  botao.disabled = true;
  botao.textContent = T.abrindo;
  const r = await api("/api/assinar", {method: "POST",
                       body: JSON.stringify({plano: codigo})});
  const d = await r.json();
  if (!r.ok || !d.url) {
    botao.disabled = false;
    $("aviso_teste").textContent = d.erro || T.erro_assinar;
    return;
  }
  // A confirmação é uma página do admin do Shopify: ela não pode ser carregada
  // dentro do nosso iframe. Tem que sair pra janela de cima, senão o lojista vê
  // um retângulo branco no lugar da tela de aprovar a cobrança.
  window.top.location.href = d.url;
}

async function carregarUso() {
  const r = await api("/api/uso");
  const d = await r.json();
  if (!r.ok) { $("plano").textContent = d.erro || ""; return; }
  limiteModelos = d.limite_modelos || 0;
  quantosModelos = d.modelos || 0;
  $("plano").textContent = d.limite_mes
    ? T.plano_com_limite.replace("%s", d.nome_do_plano)
        .replace("%d", d.etiquetas_no_mes).replace("%d", d.limite_mes)
    : T.plano_sem_limite.replace("%s", d.nome_do_plano);
  // Térmica é do plano pago. Deixar o botão clicável pra tomar 402 depois seria
  // prometer o que não entrega.
  $("zpl").title = d.motores.indexOf("zpl") < 0 ? T.termica_e_do_pro : "";
}

async function comecar() {
  const r = await api("/api/formatos");
  const d = await r.json();
  CAMPOS = d.campos || [];

  $("formato").innerHTML = "";
  (d.formatos || []).forEach(function (f) {
    const o = document.createElement("option");
    o.value = f.codigo;
    // O nome do formato já diz "30 por folha" quando é folha. Repetir aqui
    // gerava "5160 — 30 per sheet — 66.7×25.4mm (30 per sheet)".
    o.textContent = f.nome + " — " + f.largura_mm + "×" + f.altura_mm + "mm";
    $("formato").appendChild(o);
  });

  const marcados = d.padrao || [];
  $("campos").innerHTML = "";
  CAMPOS.forEach(function (c) {
    const l = document.createElement("label");
    const i = document.createElement("input");
    i.type = "checkbox"; i.className = "campo"; i.value = c.chave;
    i.checked = marcados.indexOf(c.chave) >= 0;
    i.addEventListener("change", mudou);
    l.appendChild(i);
    l.appendChild(document.createTextNode(" " + c.nome));
    $("campos").appendChild(l);
  });

  ["formato", "simbolo", "posicao", "decimal", "simbologia", "rotulo_sku", "dx", "dy"]
    .forEach(function (id) { $(id).addEventListener("change", mudou); });

  $("modelo").addEventListener("change", function () {
    abrirModelo($("modelo").value);
  });
  $("salvar").addEventListener("click", function () { comTrava(guardar); });
  $("duplicar").addEventListener("click", function () {
    comTrava(async function () {
      const r = await api("/api/modelos/" + modeloAtual + "/copia", {method: "POST"});
      const d = await r.json();
      if (!r.ok) { avisar(d.erro || T.erro_duplicar); return; }
      await carregarModelos(d.id);
      await abrirModelo(d.id);
    });
  });
  // Apagar em dois cliques em vez de uma caixa do navegador: dentro do iframe
  // do Shopify um `confirm()` pode ser bloqueado, e aí o botão não faria nada —
  // sem erro, sem explicação.
  $("apagar").addEventListener("click", async function () {
    if ($("apagar").dataset.certeza !== "1") {
      $("apagar").dataset.certeza = "1";
      $("apagar").textContent = T.apagar_mesmo;
      setTimeout(function () {
        $("apagar").dataset.certeza = "0";
        $("apagar").textContent = T.apagar;
      }, 4000);
      return;
    }
    $("apagar").dataset.certeza = "0";
    comTrava(async function () {
      const r = await api("/api/modelos/" + modeloAtual, {method: "DELETE"});
      if (!r.ok) { avisar(T.erro_apagar); return; }
      modeloAtual = null; salvo = null; $("nome").value = "";
      await carregarModelos("");
      await atualizarPrevia();
    });
  });

  $("mais").addEventListener("click", function () {
    carregarProdutos(buscaAtual, true);
  });
  $("ver_planos").addEventListener("click", abrirPlanos);
  $("fechar_planos").addEventListener("click", function () {
    $("dlg_planos").close();
  });

  $("buscar").addEventListener("click", function () { carregarProdutos($("busca").value); });
  $("busca").addEventListener("keydown", function (e) {
    if (e.key === "Enter") carregarProdutos($("busca").value);
  });
  // Imprime SEMPRE o que está na tela, salvo ou não — é o que a prévia mostra.
  // O `modelo_id` vai junto só pro histórico saber de qual modelo veio.
  $("pdf").addEventListener("click", function () {
    comTrava(function () {
      return baixar("/api/imprimir", {motor: "pdf", receita: receita(),
                    itens: fila(), modelo_id: modeloAtual}, "etiquetas.pdf");
    });
  });
  $("zpl").addEventListener("click", function () {
    comTrava(function () {
      return baixar("/api/imprimir", {motor: "zpl", receita: receita(),
                    itens: fila(), modelo_id: modeloAtual}, "etiquetas.zpl");
    });
  });
  $("regua").addEventListener("click", function () {
    comTrava(function () {
      return baixar("/api/calibracao.pdf", {receita: receita()},
                    "regua-de-calibracao.pdf");
    });
  });

  contar();
  atualizarPrevia();
  await carregarUso();
  await carregarModelos("");
  carregarProdutos("");
}

comecar().catch(function () {
  $("plano").textContent = T.erro_servidor;
});
</script>
</body></html>"""


@rotas.get("/")
def casa():
    loja = request.args.get("shop", "")

    # Sem `shop` é gente chegando pela URL direto, não pelo admin. Não é erro.
    if not loja:
        return render_template_string(FORA, T=textos.tabela(g.idioma))

    if not dominio.valido(loja):
        abort(400, textos.t("erro_dominio", g.idioma))

    registro = lojas.buscar(loja)
    if not registro or not registro["ativa"]:
        destino = "%s/instalar?shop=%s" % (config.URL_DO_APP,
                                           dominio.normalizar(loja))
        if request.args.get("embedded") == "1":
            return render_template_string(ESCAPAR, destino=destino,
                                          T=textos.tabela(g.idioma))
        return redirect(destino)

    return render_template_string(CASCA, chave_api=config.CHAVE_API,
                                  T=textos.tabela(g.idioma), idioma=g.idioma)
