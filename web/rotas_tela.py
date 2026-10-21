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
/* A coluna acompanha a rolagem, e ROLA POR DENTRO quando não cabe.
   Sem o max-height, ela ficava pregada no topo e a parte de baixo — a
   calibração, que é a resposta pra reclamação nº 1 — só aparecia depois de
   rolar até o fim de uma lista de 118 produtos. Numa tela de notebook ela era,
   na prática, inalcançável. Apareceu tentando fotografar a tela.

   O desconto de 110px é o cabeçalho mais as margens: sem ele a coluna cabia só
   DEPOIS que a página rolava o bastante pra ela grudar no topo, e numa loja com
   poucos produtos não havia rolagem nenhuma pra dar. */
.direita{position:sticky;top:16px;display:flex;flex-direction:column;gap:16px;
         max-height:calc(100vh - 110px);overflow-y:auto;scrollbar-width:thin;
         padding-right:2px}
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

<dialog id="dlg_cod">
  <h2>{{ T.codigo_titulo }}</h2>
  <p class="aviso">{{ T.codigo_aviso_escrita }}</p>
  <label for="cod_modo">{{ T.codigo_modo }}</label>
  <select id="cod_modo">
    <option value="interno">{{ T.codigo_modo_interno }}</option>
    <option value="gs1">{{ T.codigo_modo_gs1 }}</option>
    <option value="sku">{{ T.codigo_modo_sku }}</option>
  </select>
  <div id="cod_linha_prefixo" hidden>
    <label for="cod_prefixo">{{ T.codigo_prefixo }}</label>
    <input type="text" id="cod_prefixo" spellcheck="false" inputmode="numeric">
    <p class="ajuda" id="cod_cabem"></p>
  </div>
  <!-- A frase que diz ONDE aquele código vale. Fica em destaque e MUDA com o
       modo: código interno apresentado como GTIN é mentira com consequência
       comercial pro lojista. É a regra 5 do desenho. -->
  <p class="aviso" id="cod_aviso_modo"></p>
  <div class="linha" style="margin:10px 0 0">
    <button class="b" id="cod_ver">{{ T.gerar_ver }}</button>
    <button class="b" id="cod_desfazer">{{ T.gerar_desfazer }}</button>
  </div>
  <p class="ajuda" id="cod_resumo">{{ T.gerar_nada_ainda }}</p>
  <div id="cod_tabela"></div>
  <div class="linha" style="justify-content:flex-end;margin:14px 0 0">
    <button class="b forte" id="cod_aplicar" disabled></button>
    <button class="b" id="fechar_cod">{{ T.fechar }}</button>
  </div>
</dialog>

<dialog id="dlg_sku">
  <h2>{{ T.gerar_titulo }}</h2>
  <p class="aviso">{{ T.gerar_aviso_escrita }}</p>
  <label for="sku_molde">{{ T.gerar_molde }}</label>
  <input type="text" id="sku_molde" spellcheck="false">
  <p class="ajuda">{{ T.gerar_molde_ajuda }}</p>
  <div class="linha" style="margin:10px 0 0">
    <button class="b" id="sku_ver">{{ T.gerar_ver }}</button>
    <button class="b" id="sku_desfazer">{{ T.gerar_desfazer }}</button>
  </div>
  <p class="ajuda" id="sku_resumo">{{ T.gerar_nada_ainda }}</p>
  <div id="sku_tabela"></div>
  <div class="linha" style="justify-content:flex-end;margin:14px 0 0">
    <button class="b forte" id="sku_aplicar" disabled></button>
    <button class="b" id="fechar_sku">{{ T.fechar }}</button>
  </div>
</dialog>

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
        <button class="b" id="abrir_sku" style="margin:0 0 9px">{{ T.gerar_sku }}</button>
        <button class="b" id="abrir_cod" style="margin:0 0 9px">{{ T.codigo_botao }}</button>
      <select id="filtro" style="margin:0 0 9px">
        <option value="">{{ T.filtro_todos }}</option>
        <option value="sem_codigo">{{ T.filtro_sem_codigo }}</option>
        <option value="sem_sku">{{ T.filtro_sem_sku }}</option>
        <option value="sem_nenhum">{{ T.filtro_sem_nenhum }}</option>
      </select>
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

      <div id="medida_livre" hidden style="margin:9px 0 0">
        <div class="par">
          <div>
            <label for="largura_mm">{{ T.largura_mm }}</label>
            <input type="number" id="largura_mm" step="0.1" value="50.8">
          </div>
          <div>
            <label for="altura_mm">{{ T.altura_mm }}</label>
            <input type="number" id="altura_mm" step="0.1" value="25.4">
          </div>
        </div>
        <p class="ajuda">{{ T.medida_ajuda }}</p>
      </div>

      <details>
        <summary>{{ T.preco_e_codigo }}</summary>
        <div class="par" style="margin:10px 0 0">
          <div>
            <label for="simbolo">{{ T.simbolo }}</label>
            <input type="text" id="simbolo" value="{{ T.exemplo_moeda }}" maxlength="4">
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
            <!-- O padrão segue o idioma: dólar com vírgula decimal ("$ 24,90")
                 é o tipo de detalhe que faz um lojista americano desconfiar do
                 app inteiro. Só apareceu na captura de tela. -->
            <select id="decimal">
              <option value="," {% if idioma != 'en' %}selected{% endif %}>24,90</option>
              <option value="." {% if idioma == 'en' %}selected{% endif %}>24.90</option>
            </select>
          </div>
          <div>
            <label for="simbologia">{{ T.tipo_de_codigo }}</label>
            <select id="simbologia">
              <option value="EAN13">EAN-13</option>
              <option value="UPCA">UPC-A</option>
              <option value="CODE128">Code 128</option>
              <option value="ITF14">ITF-14</option>
              <option value="QRCODE">QR Code</option>
            </select>
          </div>
        </div>
        <label style="display:flex;align-items:center;gap:8px;margin:11px 0 0;
                      font-size:13px;color:var(--tinta);cursor:pointer">
          <input type="checkbox" id="rotulo_sku" checked> {{ T.rotulo_sku }}
        </label>
        <label style="display:flex;align-items:center;gap:8px;margin:7px 0 0;
                      font-size:13px;color:var(--tinta);cursor:pointer">
          <input type="checkbox" id="digitos_do_codigo" checked>
          {{ T.digitos_do_codigo }}
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
const MOLDE_PADRAO = {{ molde_padrao|tojson }};
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
  const r = await fetch(caminho, Object.assign({}, opcoes, {headers: cab}));
  // A autorização do app com o Shopify vence sozinha depois de 90 dias parada.
  // Quando isso acontece o servidor manda a frase certa e o que fazer — e sem
  // isto aqui cada painel mostraria só "erro do servidor", que não diz ao
  // lojista que existe saída. Recusar sem mostrar o caminho é onde ele fecha a
  // aba. O `clone` existe pra quem chamou ainda poder ler o corpo.
  if (r.status === 403) avisarSeForReconectar(r.clone());
  return r;
}

let jaAvisouReconectar = false;

async function avisarSeForReconectar(resposta) {
  if (jaAvisouReconectar) return;      // três chamadas em paralelo, um aviso só
  try {
    const d = await resposta.json();
    if (d.motivo !== "precisa_reinstalar") return;
    jaAvisouReconectar = true;
    avisar(d.erro, "aviso");
    $("plano").textContent = "";
  } catch (e) { /* corpo que não é JSON não muda nada */ }
}

const $ = function (id) { return document.getElementById(id); };
const itens = [];                       // o catálogo carregado
// id da variante → {item, quantidade}. Guarda o ITEM INTEIRO, e não só a
// quantidade, por causa de um defeito medido: a fila de impressão era montada
// percorrendo `itens`, que é zerado a cada busca nova. Escolher um produto,
// buscar outra coisa e escolher o segundo dava **contador dizendo 2 e PDF com
// 1** — perda silenciosa, no exato momento de imprimir.
//
// Guardando o item, a escolha sobrevive à busca seguinte. E a ordem do Map é a
// ordem em que a pessoa escolheu, que é a ordem certa de sair no papel.
const escolhidos = new Map();

// A receita é só ESCOLHA. Nenhuma coordenada, nenhum milímetro: quem traduz
// isso em etiqueta é o servidor, pelo mesmo caminho que imprime.
function receita() {
  return {
    formato: $("formato").value,
    largura_mm: parseFloat($("largura_mm").value) || 0,
    altura_mm: parseFloat($("altura_mm").value) || 0,
    campos: Array.from(document.querySelectorAll(".campo:checked"))
                 .map(function (c) { return c.value; }),
    simbolo: $("simbolo").value,
    simbolo_depois: $("posicao").value === "depois",
    separador_decimal: $("decimal").value,
    separador_milhar: $("decimal").value === "," ? "." : ",",
    rotulo_sku: $("rotulo_sku").checked,
    digitos_do_codigo: $("digitos_do_codigo").checked,
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

let LIVRE = null;            // o codigo e os limites da medida livre

function mostrarMedidaLivre() {
  $("medida_livre").hidden = !LIVRE || $("formato").value !== LIVRE.codigo;
}

function aplicarReceita(r) {
  const set = function (id, v) { if (v !== undefined) $(id).value = v; };
  set("formato", r.formato);
  if (r.largura_mm) { $("largura_mm").value = r.largura_mm; }
  if (r.altura_mm) { $("altura_mm").value = r.altura_mm; }
  mostrarMedidaLivre();
  set("simbolo", r.simbolo);
  set("posicao", r.simbolo_depois ? "depois" : "antes");
  set("decimal", r.separador_decimal);
  set("simbologia", r.simbologia);
  set("dx", r.desvio_x_mm);
  set("dy", r.desvio_y_mm);
  $("rotulo_sku").checked = r.rotulo_sku !== false;
  $("digitos_do_codigo").checked = r.digitos_do_codigo !== false;
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
  for (const escolha of escolhidos.values()) return escolha.item;
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
  // Duas coisas diferentes podem sumir da etiqueta, e o lojista precisa saber
  // qual: um CAMPO que não coube (resolve escolhendo papel maior) e o CÓDIGO
  // que não bipa (resolve arrumando o cadastro do produto).
  const recados = [];
  if (d.nao_coube && d.nao_coube.length) {
    recados.push(T.nao_coube.replace("%s",
      d.nao_coube.map(function (c) { return nomeDoCampo(c); }).join(", ")));
  }
  if (d.codigo_invalido) {
    recados.push(T.codigo_invalido.replace("%s", d.codigo_invalido));
  }
  $("recado").innerHTML = "";
  recados.forEach(function (texto) {
    const p = document.createElement("p");
    p.className = "aviso";
    p.textContent = texto;
    $("recado").appendChild(p);
  });
}

let CAMPOS = [];
function nomeDoCampo(chave) {
  const c = CAMPOS.find(function (x) { return x.chave === chave; });
  return c ? c.nome.toLowerCase() : chave;
}

// O único lugar que põe alguém na fila. A caixinha, o leitor de código e
// qualquer coisa futura passam por aqui — senão um deles esquece de guardar o
// item e o produto some do PDF de novo.
function escolher(it, quantidade) {
  escolhidos.set(it.variante.id,
                 {item: it, quantidade: Math.max(1, quantidade || 1)});
}

function contar() {
  let total = 0;
  escolhidos.forEach(function (e) { total += e.quantidade; });
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
    const jaEscolhido = escolhidos.get(id);
    q.type = "number"; q.min = "1";
    q.value = (jaEscolhido && jaEscolhido.quantidade) || it.quantidade || 1;
    q.setAttribute("aria-label", T.quantas_de.replace("%s", it.produto.titulo));
    tdQ.appendChild(q);

    marca.addEventListener("change", function () {
      if (marca.checked) escolher(it, parseInt(q.value, 10) || 1);
      else escolhidos.delete(id);
      contar(); pedirPrevia();
    });
    q.addEventListener("change", function () {
      if (escolhidos.has(id)) escolher(it, Math.max(1, parseInt(q.value, 10) || 1));
      contar();
    });

    tr.appendChild(tdC); tr.appendChild(tdN); tr.appendChild(tdB); tr.appendChild(tdQ);
    corpo.appendChild(tr);
  });

  tabela.appendChild(corpo);
  $("lista").innerHTML = "";
  $("lista").appendChild(tabela);
  // Avisa quem estiver esperando a lista existir. Serve pras cenas de captura
  // de tela, que precisavam adivinhar quanto tempo o catálogo demora — e
  // adivinhavam errado, capturando a tela antes de os produtos chegarem.
  document.dispatchEvent(new Event("lista-pronta"));
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
  const filtro = $("filtro") ? $("filtro").value : "";
  if (filtro) url += "&filtro=" + encodeURIComponent(filtro);
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

  // Os dois recados do catálogo moram no mesmo lugar e NÃO podem se apagar.
  // A primeira versão deixava cada um escrever `innerHTML` direto, e aí o
  // último a rodar apagava o outro — o lojista com produto de 100+ variantes
  // perdia esse aviso assim que ligasse um filtro.
  $("aviso_catalogo").innerHTML = "";

  function recado(texto, classe) {
    const p = document.createElement("p");
    p.className = classe;
    p.textContent = texto;
    $("aviso_catalogo").appendChild(p);
  }

  // Com filtro ligado, dizer quantos achou SEM dizer entre quantos procurou
  // faria o lojista achar que "3 sem código" é a loja inteira.
  if (d.filtro && d.varridos) {
    recado(T.filtro_resultado
             .replace("%d", (d.itens || []).length).replace("%d", d.varridos)
           + (d.parou_no_teto ? " " + T.filtro_teto.replace("%d", d.varridos) : ""),
           "ajuda");
  }

  // Produto com mais de 100 variantes vem cortado pela consulta. Sumir em
  // silêncio faria o lojista imprimir a prateleira faltando tamanhos.
  if (d.variantes_cortadas && d.variantes_cortadas.length) {
    recado(T.variantes_cortadas.replace("%s", d.variantes_cortadas.join(", ")),
           "aviso");
  }
  if (!continuar) escolherOEscaneado();
  desenharLista();
}

// Um leitor de código de barras é um TECLADO: ele digita o código e manda
// Enter. Ou seja, ele cai na busca — e a busca já devolve exatamente aquele
// produto. Só faltava marcar.
//
// A regra é o casamento EXATO com o código de barras ou o SKU, e não "a busca
// devolveu um só". Alguém digitando "caneca" e recebendo um resultado não pediu
// pra escolher; um código idêntico ao cadastrado só chega de leitor ou de
// cópia-e-cola, e nos dois casos a intenção é aquele produto.
function escolherOEscaneado() {
  const lido = (buscaAtual || "").trim();
  if (!lido) return;

  const achados = itens.filter(function (it) {
    return (it.variante.codigo_barras || "").trim() === lido
        || (it.variante.sku || "").trim().toLowerCase() === lido.toLowerCase();
  });
  // Dois produtos com o mesmo código é cadastro duplicado. Escolher um dos dois
  // por conta própria seria adivinhar qual — a lista fica aí pra pessoa decidir.
  if (achados.length !== 1) return;

  const it = achados[0];
  if (escolhidos.has(it.variante.id)) return;   // bipou duas vezes: não duplica
  escolher(it, it.quantidade || 1);
  contar();
  pedirPrevia();

  // Deixa o texto selecionado e o foco na busca: o próximo bipe substitui este
  // em vez de emendar nele. É o que transforma "bipar" em bipar, bipar, bipar.
  const b = $("busca");
  b.focus();
  b.select();
}

function fila() {
  // Sai do `escolhidos`, não do `itens`: `itens` só tem o resultado da busca
  // ATUAL, e montar a fila a partir dele apagava do PDF tudo que foi escolhido
  // em buscas anteriores — com o contador continuando a dizer que estava lá.
  const saida = [];
  escolhidos.forEach(function (e) {
    saida.push(Object.assign({}, e.item, {quantidade: e.quantidade}));
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

// ------------------------------------------------------------- os geradores
//
// Duas janelas, um caminho só. A de SKU e a de código de barras fazem
// exatamente a mesma coisa: mostrar a tabela INTEIRA antes de qualquer letra
// ir pro catálogo, e gravar só o que o lojista marcou.
//
// Nasceram como duas cópias, e duas cópias da parte perigosa do app divergem
// na terceira correção. O que muda entre elas está só na tabela abaixo.
//
// Etiqueta errada custa uma folha de papel. Código errado em 300 produtos
// custa o inventário da loja.
const GERADORES = {
  sku: {
    rota: "/api/skus",
    valor: function (l) { return l.sku; },
    atual: function (l) { return l.sku_atual; },
    colunas: function () {
      return [T.gerar_col_produto, T.gerar_col_atual, T.gerar_col_novo];
    },
    extra: null,
    aplicar: function () { return T.gerar_aplicar; },
    resumo: function () { return T.gerar_resumo; },
    escolhas: function () {
      return {molde: $("sku_molde").value, filtro: $("filtro").value};
    },
  },
  cod: {
    rota: "/api/codigos",
    valor: function (l) { return l.codigo; },
    atual: function (l) { return l.codigo_atual; },
    colunas: function () {
      return [T.gerar_col_produto, T.codigo_col_atual, T.gerar_col_novo,
              T.codigo_col_tipo];
    },
    // A coluna que diz QUE TIPO de número é. Código interno apresentado como
    // GTIN é mentira com consequência comercial — regra 5 do desenho.
    extra: function (l) { return l.tipo || ""; },
    aplicar: function () { return T.codigo_aplicar; },
    resumo: function () { return T.codigo_resumo; },
    escolhas: function () {
      return {modo: $("cod_modo").value, prefixo: $("cod_prefixo").value,
              filtro: $("filtro").value};
    },
  },
};

function gerMarcadas(p) {
  return Array.from(document.querySelectorAll(
    "#" + p + "_tabela input[type=checkbox]:checked"
  )).map(function (c) { return c.value; });
}

function gerAtualizarBotao(p) {
  const n = gerMarcadas(p).length;
  $(p + "_aplicar").disabled = n === 0;
  $(p + "_aplicar").textContent = GERADORES[p].aplicar().replace("%d", n);
}

function gerAvisar(p, texto) {
  $(p + "_resumo").textContent = texto || T.erro_servidor;
}

function gerDesenhar(p, d) {
  const g = GERADORES[p];
  const linhas = d.linhas || [];
  const podem = linhas.filter(function (l) { return g.valor(l) && !l.pulado; });

  let resumo = g.resumo().replace("%d", podem.length)
                        .replace("%d", d.varridos || 0);
  // A conferência de repetidos só alcança o que foi varrido. Dizer isso é
  // melhor que deixar o lojista achar que vale pro catálogo inteiro.
  if (d.conferencia_completa === false) resumo += " " + T.gerar_parcial;
  // O ⚠ por linha obriga a ler a tabela inteira pra perceber que o molde nao
  // distingue nada. Dito no resumo, o lojista ve antes de gravar.
  const comSufixo = podem.filter(function (l) { return l.aviso; }).length;
  if (comSufixo) {
    resumo += " " + T.gerar_repetidos.replace("%d", comSufixo);
  }
  $(p + "_resumo").textContent = resumo;

  const tabela = document.createElement("table");
  const cabeca = g.colunas().map(function (c) { return "<th>" + c + "</th>"; });
  tabela.innerHTML = "<thead><tr><th class=c></th>" + cabeca.join("") +
                     "</tr></thead>";
  const corpo = document.createElement("tbody");

  linhas.forEach(function (l) {
    const tr = document.createElement("tr");

    const tdC = document.createElement("td");
    if (g.valor(l) && !l.pulado) {
      const c = document.createElement("input");
      c.type = "checkbox";
      c.value = l.variante_id; c.checked = true;
      c.addEventListener("change", function () { gerAtualizarBotao(p); });
      tdC.appendChild(c);
    }

    const tdN = document.createElement("td");
    const t1 = document.createElement("div"); t1.className = "t";
    t1.textContent = l.produto || "";
    const t2 = document.createElement("div"); t2.className = "s";
    t2.textContent = l.variante || "";
    tdN.appendChild(t1); tdN.appendChild(t2);

    const tdA = document.createElement("td"); tdA.className = "s";
    tdA.textContent = g.atual(l) || "\u2014";

    const tdV = document.createElement("td");
    // Linha pulada mostra o MOTIVO no lugar do valor. Sumir em silêncio é o
    // defeito que este app existe pra não ter.
    tdV.textContent = l.pulado ? l.pulado
                               : (g.valor(l) + (l.aviso ? " \u26a0" : ""));
    tdV.className = l.pulado ? "s" : "t";
    if (l.aviso) tdV.title = l.aviso;

    tr.appendChild(tdC); tr.appendChild(tdN); tr.appendChild(tdA);
    tr.appendChild(tdV);
    if (g.extra) {
      const tdE = document.createElement("td"); tdE.className = "s";
      tdE.textContent = g.extra(l);
      tr.appendChild(tdE);
    }
    corpo.appendChild(tr);
  });

  tabela.appendChild(corpo);
  $(p + "_tabela").innerHTML = "";
  $(p + "_tabela").appendChild(tabela);
  gerAtualizarBotao(p);
}

async function gerPrevia(p) {
  const g = GERADORES[p];
  $(p + "_resumo").textContent = T.carregando;
  const r = await api(g.rota + "/previa",
                      {method: "POST", body: JSON.stringify(g.escolhas())});
  const d = await r.json();
  if (!r.ok) { $(p + "_tabela").innerHTML = ""; gerAvisar(p, d.erro); return; }
  // O aviso do modo vem do servidor junto da tabela: quem manda nele é o
  // gerador, não a tela.
  if (d.aviso_do_modo && $(p + "_aviso_modo")) {
    $(p + "_aviso_modo").textContent = d.aviso_do_modo;
  }
  gerDesenhar(p, d);
}

async function gerAplicar(p) {
  const g = GERADORES[p];
  const marcadas = gerMarcadas(p);
  if (!marcadas.length) return;
  $(p + "_aplicar").disabled = true;
  const corpo = Object.assign(g.escolhas(), {variantes: marcadas});
  const r = await api(g.rota + "/aplicar",
                      {method: "POST", body: JSON.stringify(corpo)});
  const d = await r.json();
  if (!r.ok) { gerAvisar(p, d.erro); gerAtualizarBotao(p); return; }

  const quantos = d.gravados || 0;
  // Zero gravado não usa o texto de "dá para desfazer": não há o que desfazer,
  // e mandar o lojista procurar isso é pior que não dizer nada.
  let texto = quantos ? T.gerar_gravados.replace("%d", quantos)
                      : T.gerar_nada_gravado;
  // As recusas do Shopify aparecem. Gravar 8 de 10 e dizer "gravei" seria a
  // mesma meia verdade que o app recusa em todo lugar.
  if (d.falhas && d.falhas.length) texto += " \u2014 " + d.falhas.join("; ");
  gerAvisar(p, texto);
  // A tabela só sai se algo mudou. Apagar a prévia depois de uma gravação que
  // falhou tiraria da tela justamente o que serve pra tentar de novo.
  if (quantos) {
    $(p + "_tabela").innerHTML = "";
    carregarProdutos($("busca").value);
  }
  gerAtualizarBotao(p);
}

async function gerDesfazer(p) {
  const r = await api(GERADORES[p].rota + "/desfazer",
                      {method: "POST", body: "{}"});
  const d = await r.json();
  if (!r.ok) { gerAvisar(p, d.erro); return; }
  const quantos = d.desfeitos || 0;
  let texto = quantos ? T.gerar_desfeitos.replace("%d", quantos)
                      : T.gerar_nada_gravado;
  if (d.falhas && d.falhas.length) texto += " \u2014 " + d.falhas.join("; ");
  gerAvisar(p, texto);
  if (quantos) {
    $(p + "_tabela").innerHTML = "";
    carregarProdutos($("busca").value);
  }
}

function gerLigar(p) {
  $("abrir_" + p).addEventListener("click", function () {
    $(p + "_tabela").innerHTML = "";
    $(p + "_resumo").textContent = T.gerar_nada_ainda;
    gerAtualizarBotao(p);
    $("dlg_" + p).showModal();
  });
  $("fechar_" + p).addEventListener("click", function () {
    $("dlg_" + p).close();
  });
  $(p + "_ver").addEventListener("click", function () {
    comTrava(function () { return gerPrevia(p); });
  });
  $(p + "_aplicar").addEventListener("click", function () {
    comTrava(function () { return gerAplicar(p); });
  });
  $(p + "_desfazer").addEventListener("click", function () {
    comTrava(function () { return gerDesfazer(p); });
  });
}

// O prefixo GS1 só aparece no modo que precisa dele, e o aviso de ONDE o
// código vale muda junto com o modo — antes da primeira prévia, inclusive. O
// lojista não pode escolher "código interno" sem ler que ele não serve pra
// vender em outra loja.
function codAtualizarModo() {
  const modo = $("cod_modo").value;
  $("cod_linha_prefixo").hidden = modo !== "gs1";
  $("cod_aviso_modo").textContent = T["codigo_aviso_" + modo] || "";
  codContarPrefixo();
}

function codContarPrefixo() {
  const p = ($("cod_prefixo").value || "").trim();
  // Prefixo longo é prefixo de empresa pequena: com 11 dígitos sobram 9
  // números. Vale dizer isso ANTES de gravar 300 produtos e parar no décimo.
  const cabem = /^[0-9]{4,11}$/.test(p) ? Math.pow(10, 12 - p.length) - 1 : 0;
  $("cod_cabem").textContent = cabem
    ? T.codigo_cabem.replace("%s", cabem.toLocaleString(IDIOMA))
    : "";
}

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
  // Medida livre entra por último, depois do catálogo: quem tem uma etiqueta
  // conhecida escolhe pelo nome, e só quem não achou a dele desce até aqui.
  if (d.livre) {
    LIVRE = d.livre;
    const o = document.createElement("option");
    o.value = d.livre.codigo;
    o.textContent = d.livre.nome;
    $("formato").appendChild(o);
    $("largura_mm").min = $("altura_mm").min = d.livre.menor_mm;
    $("largura_mm").max = $("altura_mm").max = d.livre.maior_mm;
  }
  $("formato").addEventListener("change", mostrarMedidaLivre);
  mostrarMedidaLivre();

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

  ["formato", "simbolo", "posicao", "decimal", "simbologia", "rotulo_sku",
   "digitos_do_codigo", "largura_mm", "altura_mm", "dx", "dy"]
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

  // O padrao vem do modulo, pra tela e gerador nao poderem divergir.
  $("sku_molde").value = MOLDE_PADRAO;
  gerLigar("sku");
  gerLigar("cod");
  $("cod_modo").addEventListener("change", codAtualizarModo);
  $("cod_prefixo").addEventListener("input", codContarPrefixo);
  codAtualizarModo();

  $("filtro").addEventListener("change", function () {
    carregarProdutos($("busca").value);
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
