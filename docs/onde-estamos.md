# Onde estamos

**Atualizado em 30/08/2026.** Documento vivo: estado atual e próxima ação. Se
divergir dos outros documentos, este está mais novo.

---

## Em uma frase

O app está pronto, no ar e funcionando numa loja real. **A primeira mensagem foi
enviada.** Não falta código; falta um lojista.

---

## O que aconteceu em 30/08/2026

Foi um dia longo. Em ordem, e o que cada coisa custou ou revelou.

### O terreno mudou de figura

A pesquisa que originou o projeto tinha um buraco: olhou as avaliações ruins do
app oficial e **nunca perguntou quem já atendia aquela gente**. Atendia — o
*Yanet* tem 4,9 com 448 avaliações, e o *LabelFast* nasceu em 06/07/2026 com a
mesma lista de diferenciais. Ver [`quem-mais-esta-aqui.md`](quem-mais-esta-aqui.md).

Isso **não** matou o projeto: concorrente bom prova que o mercado paga, e a meta
de R$ 500–2.000/mês são 12 a 50 lojas pagantes.

### O que foi construído

| | por quê |
|---|---|
| Avery 5167 e rolo 1"×1" | pedidos por nome nas avaliações |
| Medida livre (8–300mm) | idem |
| ITF-14 | código de caixa de atacado; o único dos 3 símbolos que faltavam que muda algo |
| Dígitos sob o código viram escolha | na 5167 faltavam 0,07mm pro SKU caber |
| Grátis 100 → 200 etiquetas | é o que a categoria dá |
| Leitor de código enfileira sozinho | bipar, bipar, bipar, imprimir |
| Prévia diz por que o código sumiu | sumir calado é o defeito que o app combate |

### Os defeitos que apareceram no caminho

Todos achados **medindo**, nenhum lendo código:

1. **O app nunca conferia se o código cabia na LARGURA.** Um EAN-13 precisa de
   28,3mm; a etiqueta de 1"×1" tem 25,4mm. Medida livre teria tornado isso rotina.
2. **O QR saía de tamanhos diferentes por impressora** — 18,0mm no PDF, 16,5mm no
   ZPL. Com URL longa, ia para fora da etiqueta.
3. **A Shopify parou de aceitar o token que não expira**, e o app parou de listar
   produtos em produção. Migrado para token de 1h + renovação de 90 dias.
4. **A renovação tinha corrida:** a tela dispara 3 chamadas paralelas, e 2 de 3
   mandavam o lojista reinstalar. Toda vez que ele abrisse o app depois de 1h.
5. **UPC-A com dígito verificador errado ia pro papel** — bipa o produto errado
   no caixa. A conferência existia só para EAN-13.
6. **A fila de impressão perdia produto escolhido em busca anterior.** Contador
   dizia 2, PDF saía com 1.
7. **A instalação tentava assinar os webhooks de privacidade pela API**, que não
   aceita. Falhava em silêncio — e sem a declaração estática o app é **reprovado**.
8. **O ITF-14 sairia 21% mais largo na Zebra** que no PDF, por razão de barra
   diferente entre as bibliotecas.

### O estado técnico

**976 checagens, 71 de 71 sabotagens.** No ar em
`https://etikbarcode.pythonanywhere.com`.

---

## A decisão tomada

**O app não gera código de barras**, e o gatilho para reabrir está escrito em
[`decisao-gerar-codigo.md`](decisao-gerar-codigo.md): *um lojista de verdade
dizer que não consegue usar porque os produtos dele não têm código*.

---

## A próxima ação

### Feito
- [x] **Patch Magazine** (Reino Unido) — enviada em **30/08/2026** para
      `contact@patchmagazine.co.uk`, do `rjuan.andrade99@gmail.com`

### Próximas — contatos já achados
- [ ] **THATS-RALLY** (Alemanha) — `info@thats-rally.de`
- [ ] **Bhumi Organic Cotton** (Austrália) — `help@bhumi.com.au`
- [ ] **Maiocchi** (Austrália) — `e-boutique@maiocchi.com.au`, guardar pra
      próxima leva: mesma queixa da Bhumi

### E uma descoberta que encolheu o canal

**A Shopify não expõe a loja de quem avalia.** Sobra nome e país. De sete
tentadas, **quatro são alcançáveis** — Saratoga só tem telefone, e Frip'Dream e
The Scented Cardinal não existem em busca nenhuma, nem no Instagram.

Marca com loja física é encontrável; loja pequena só-online não é. Isso joga a
favor (loja física é quem imprime etiqueta de prateleira), mas **derruba a
premissa do plano**: 8 mensagens viraram 4, e a expectativa de resposta caiu de
1–2 para 0,4–1,2. O canal sozinho provavelmente não dá o sinal que justificaria
adiar a submissão.

### As regras combinadas

- **Duas ou três por dia**, não todas de uma vez. Contato de lojista é **não
  renovável**: só existe uma primeira mensagem por loja.
- **Guardar duas na reserva.** Se as seis primeiras derem zero, reescrever a
  mensagem e testar nessas duas — é a única forma de separar "e-mail frio não
  funciona" de "meu e-mail não funciona".
- **Expectativa honesta:** 10 a 30% de resposta. Com oito enviadas, espera-se
  **uma ou duas**. Zero de três não significa nada; zero de oito é sinal.
- **Critério de parada:** duas semanas, cinco enviadas, nenhuma resposta → o
  canal está errado e muda.

### E se alguém disser sim

É só aí que se gasta dinheiro. A lista completa está em
[`antes-de-submeter.md`](antes-de-submeter.md); o resumo:

1. Declarar os 3 webhooks de privacidade no painel ← **sem isto, reprovação**
2. Gravar o screencast (exigido)
3. Escrever as instruções de teste, incluindo como o revisor alcança o Pro
4. Pagar os **US$ 19** — uma vez por conta, para sempre
5. Renovar o PythonAnywhere e pôr lembrete — app fora do ar durante a revisão é
   reprovação certa

**A Shopify fica com 0% da receita até US$ 1.000.000.** Só 2,9% de processamento.
