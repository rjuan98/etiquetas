# Ficha da loja de apps — texto pronto pra colar

Escrito em inglês porque é onde está o mercado que a gente mediu: as 466
avaliações do app oficial, as reclamações sobre etiqueta Avery, o volume de
lojas. Ver `loja/cobranca.py` pra o raciocínio completo.

> **Revisado em 30/08/2026, e o motivo importa.** A categoria não está vazia:
> tem um app com 4,9 e 448 avaliações. Ver
> [`quem-mais-esta-aqui.md`](quem-mais-esta-aqui.md).
>
> Isso muda o que esta ficha precisa fazer. Ela não pode mais dizer só "imprime
> etiqueta bonito" — isso o concorrente também faz, e há mais tempo. Ela precisa
> dizer as três coisas que **só este app** faz: a régua de calibração, a prévia
> que sai do mesmo código da impressora, e a recusa de imprimir código que não
> bipa.
>
> As três já existiam no produto e **nenhuma estava escrita aqui**.

O nome e os preços estão **decididos**. O que ainda depende de você está na
lista do fim.

---

## O nome — decidido

```
Etik Barcode Labels
```

19 dos 30 caracteres permitidos. Mantém a marca e carrega as duas palavras que o
lojista realmente digita — a maior parte das instalações vem de busca, e um nome
que ninguém procura não aparece.

**Este nome precisa ser trocado em dois lugares**, e os dois importam:

1. no painel do app, em *Configurações do app → Nome*
2. no código já está: `loja/cobranca.py`, em `NOME_DO_APP`

O do código é o que aparece na **fatura do lojista**, junto do plano — "Etik
Barcode Labels — Pro". Tem teste garantindo que o nome que a gente cria é o
mesmo que a gente reconhece de volta: se divergissem, a assinatura seria criada
e nunca reconhecida, e o lojista pagaria continuando no grátis.

---

## App introduction
*(máx. 100 caracteres — é o que aparece embaixo do nome na busca)*

```
Barcode labels that match the paper, and always scan.
```

> 52 caracteres. Duas promessas verificáveis, não adjetivo: **bate com o papel**
> (calibração + prévia fiel) e **sempre bipa** (dígito verificador conferido,
> zona muda garantida, código largo demais recusado).
>
> A versão anterior era *"print straight, every time"*. Continua verdade, mas
> "sai reto" é o que todo mundo promete. "Sempre bipa" é o que quase ninguém
> confere — e é a queixa de uma estrela que o melhor concorrente da categoria
> levou.
>
> Continua sem citar o concorrente: citar dá munição pra reprovação e parece
> briga pequena.

---

## App details
*(o parágrafo da página do app)*

```
Print barcode and price labels for your products, on sheet labels or a thermal
printer, without fighting the layout.

Pick your products — or scan them: each barcode you scan queues that product
with the quantity you have in stock — then choose what goes on the label and see
exactly what will come out. The preview
is drawn by the same code that writes the printer file, so what you see is what
the paper gets. Quantities come from your inventory, so receiving 40 units means
40 labels, not typing "1" forty times.

A barcode that wouldn't scan is never printed. Wrong check digit, wrong length
for the symbology, or simply wider than the label you picked — the app tells you
which, on screen, instead of letting you find out at the register with a queue.

If your printer drifts, print the calibration ruler, measure it with a real
ruler, and type the difference in millimetres. Your template then stays exactly
as you left it: it never changes on its own between one print run and the next.
```

> Quatro parágrafos, e o segundo e o terceiro são novos. O terceiro é o que
> nenhum concorrente escreve, porque quase nenhum confere: **código inválido não
> vira papel**.
>
> "the same code that writes the printer file" é uma afirmação forte de
> propósito, e ela se sustenta — tem teste comparando linha por linha o texto do
> SVG com o do ZPL. Todo mundo escreve "live preview"; isto é outra coisa.
>
> A última frase continua sendo resposta direta ao *"todas as minhas etiquetas
> não combinam mais"* de julho.

---

## Feature list
*(as marcações da página — curtas, uma promessa cada)*

```
Fill in missing SKUs and barcodes in bulk — review the table, then click
Nothing is written until you click, only empty fields, and you can undo it
Internal code or a GTIN from your own GS1 prefix — the app says which you got
The preview is drawn by the same code that writes the printer file
A barcode that wouldn't scan is never printed — and the app says why
Millimetre calibration for printers that drift, on both axes
Scan a barcode and the product is queued, with the quantity from stock
Any label size in millimetres, plus Avery, DYMO, Zebra and Pimaco stocks
EAN-13, UPC-A, Code 128, QR and ITF-14 for cartons
Choose every field: title, SKU, price, vendor, barcode — turn off what you don't want
Currency symbol, position and separators you control (R$ 24,90 or 24,90 €)
Templates saved and reopened exactly as you left them
```

> **A ordem mudou, e é o item 2 de [`comparacao.md`](comparacao.md).** As três
> primeiras são as únicas que o concorrente não copia da noite pro dia, e antes
> estavam enterradas ou ausentes. A antiga primeira linha ("preview the exact
> label") dizia menos que a nova: "exact" é adjetivo; "o mesmo código que
> escreve o arquivo da impressora" é afirmação que se confere.
>
> **"Scan a barcode and the product is queued"** — a frase começou menor. Na
> primeira versão desta ficha ela parava em "ready to print", porque medindo se
> viu que o leitor achava o produto e **não** marcava; prometer o clique que
> ainda existia seria mentira.
>
> Aí o clique deixou de existir: bipar o código escolhe o produto com a
> quantidade do estoque, e o campo de busca fica selecionado pro bipe seguinte.
> Bipar, bipar, bipar, imprimir. Medido de novo antes de a frase crescer.
>
> **A linha "Read-only" saiu em 20/10/2026, e a troca foi deliberada.** Ela era
> a única que nenhum concorrente podia escrever — os dois pedem escrita porque
> geram código. Mas *não gerar* era o motivo de um lojista não conseguir usar o
> app, e é o que o mercado compra: três dos cinco destaques do líder do nicho
> são sobre gerar, não sobre imprimir.
>
> As duas primeiras linhas agora são os geradores, e a segunda é a frase que
> substitui o read-only:
>
> > *"Nothing is written until you click, only empty fields, and you can undo
> > it."*
>
> Ela também é verificável, e diz mais: os concorrentes geram, mas nenhum
> promete prévia obrigatória, nunca-sobrescrever e desfazer.
>
> **A terceira linha é a que nenhum deles escreve.** Dizer ao lojista *que
> tipo* de número ele acabou de receber — código interno da faixa 2, que vale
> só na loja dele, ou GTIN do prefixo dele, que vale no mundo todo — é a
> diferença entre gerar e gerar honestamente. Código interno apresentado como
> GTIN é mentira com consequência comercial.
>
> A do € existe porque um lojista europeu reclamou disso especificamente. Item
> de lista que nasceu de uma frase real converte melhor que adjetivo.

---

## App card subtitle
*(máx. 62 caracteres — aparece nas listagens)*

```
Labels that match the paper and always scan
```

> 43 caracteres. As mesmas duas promessas da manchete, porque é esse par que
> diferencia. A anterior era *"Barcode labels for shelves, with real
> calibration"* — "for shelves" gastava 11 caracteres dizendo o óbvio.

---

## Categoria e busca

**Categoria:** Store management → Inventory management
*(alternativa: Selling products → Product display. A primeira é onde o app
oficial está, e é onde o lojista com essa dor procura.)*

**Termos de busca:**
```
barcode labels, product labels, price labels, shelf labels, label printing,
avery labels, zebra printer, zpl, dymo, sku labels, itf-14, carton labels,
custom label size, barcode scanner
```

---

## Preços
*(o que declarar na aba de pricing)*

| plano | preço | o que declarar |
|---|---|---|
| Free | US$ 0 | 1 template, 200 labels/month, sheet labels (PDF) |
| Pro | US$ 9.99/mês | Unlimited labels and templates, thermal printing (ZPL) |

**7 dias de teste grátis** no Pro.

> **O "Unlimited" do Pro é pra estar escrito com essa palavra.** É onde a nossa
> tabela é mais simples que a da categoria, e simplicidade de preço é argumento
> por si — não precisa (nem pode) citar ninguém pra isso aparecer.
>
> E o grátis é **200**, não 100: é o número que a categoria dá, e perder por 2×
> no primeiro número que o lojista compara é caro.

> **Não há terceiro plano, e isso é escolha.** Havia um "Business" prometendo
> múltiplos locais e histórico de modelos, e nenhum dos dois estava construído.
> Um terceiro nível serve pra ancorar preço, não pra encher a página — ele volta
> quando houver o que pôr nele, e aí quem diz o que é são os clientes, não a
> gente adivinhando antes do primeiro.

---

## Política de privacidade

Servida pelo próprio app:

```
{APP_URL}/privacy
```

Ela fica no repositório (`web/rotas_publicas.py`) de propósito: entra no mesmo
commit que muda o comportamento, então quando divergir do código, diverge à
vista.

---

## O que ainda falta pra submeter

> **A lista completa e conferida na fonte está em
> [`antes-de-submeter.md`](antes-de-submeter.md)** — inclusive o que REPROVA o
> app, o que já está certo, e a ordem que evita gastar antes da hora.

- [x] **Ícone** — `docs/icone.png`, 1200×1200, sem texto. Regerar: `python docs/icone.py`
- [x] **Capturas de tela** — `docs/capturas/`, quatro em 1600×900.
      Regerar: subir o servidor e `python docs/capturas.py`
- [x] **Hospedagem fixa** — `https://etikbarcode.pythonanywhere.com`, no ar
      desde 30/08/2026
- [ ] **Preencher `CONTATO_EMAIL`, `CONTATO_NOME` e `HOSPEDAGEM`** no `.env`,
      senão a política de privacidade vai ao ar dizendo "(preencha …)"
- [x] **`MODO_DEV=0`** em produção — conferido em 30/08/2026: `/dev/` responde
      404 no ar
- [x] **`CONTATO_EMAIL`, `CONTATO_NOME` e `HOSPEDAGEM`** — conferidos na página
      `/privacy` publicada, sem espaço por preencher
- [ ] **Webhooks de privacidade declarados no painel** — os três apontando pra
      `https://etikbarcode.pythonanywhere.com/webhooks`. **Sem isto o app é
      reprovado**, e é o item mais fácil de esquecer
- [ ] **Screencast** da instalação e dos recursos — exigido na submissão
- [ ] **Instruções de teste** com como o revisor alcança o plano Pro

---

## Duas coisas que eu não escreveria na ficha

**Não cite o app oficial.** É tentador — a nota 2,3 é o argumento inteiro. Mas
comparação direta com outro app é motivo de reprovação, e mesmo se passasse,
posiciona você como reação em vez de produto.

**Não venda a impressora térmica como manchete.** Todo caminho do navegador até
uma térmica exige software instalado na máquina do lojista. Prometer isso na capa
atrai justamente quem vai se frustrar antes de imprimir a primeira etiqueta.
Ela está na lista, com a ressalva, e é o lugar certo dela.
