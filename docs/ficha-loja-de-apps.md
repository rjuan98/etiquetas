# Ficha da loja de apps — texto pronto pra colar

Escrito em inglês porque é onde está o mercado que a gente mediu: as 565
avaliações do app oficial, as reclamações sobre etiqueta Avery, o volume de
lojas. Ver `loja/cobranca.py` pra o raciocínio completo.

**Nada aqui está decidido.** Onde há escolha, ela está marcada e explicada.

---

## O nome — a decisão que trava o resto

O app está cadastrado como **Etik** no painel. Antes de escrever a ficha, vale
saber o que isso custa.

A maior parte das instalações da loja de apps vem de **busca**. O lojista digita
"barcode labels" ou "product labels". Um nome que ninguém procura não aparece.

| nome | a favor | contra |
|---|---|---|
| **Etik** | curto, seu, memorável depois que a pessoa conhece | não diz nada em inglês, e ninguém busca por ele |
| **Etik Barcode Labels** | tem a palavra que as pessoas buscam, e mantém a marca | mais longo (25 de 30 caracteres) |
| **Straight Labels** | fala direto da reclamação nº 1 (etiqueta torta) | perde a marca, e "straight" tem outros sentidos |

**Minha sugestão: `Etik Barcode Labels`.** Mantém o que você já tem e coloca a
palavra buscada. O limite do Shopify é 30 caracteres e não pode conter
"Shopify".

---

## App introduction
*(máx. 100 caracteres — é o que aparece embaixo do nome na busca)*

```
Barcode and price labels that print straight, every time.
```

> 57 caracteres. Ataca a reclamação nº 1 sem citar o concorrente — citar dá
> munição pra reprovação e parece briga pequena.

---

## App details
*(o parágrafo da página do app)*

```
Print barcode and price labels for your products, on sheet labels or a thermal
printer, without fighting the layout.

Pick your products, choose what goes on the label, and see exactly what will
come out before you print. Quantities come from your inventory, so receiving 40
units means 40 labels — not typing "1" forty times.

If your printer drifts, print the calibration ruler, measure it, and type the
difference in millimetres. Your template stays exactly as you left it: it never
changes on its own between one print run and the next.
```

> Três parágrafos, três reclamações: layout que briga, digitar 1 duas mil vezes,
> etiqueta torta. A última frase é uma resposta direta ao *"todas as minhas
> etiquetas não combinam mais"* de julho.

---

## Feature list
*(as marcações da página — curtas, uma promessa cada)*

```
Preview the exact label before printing — no surprises on the paper
Quantities pulled from inventory, so no typing "1" two thousand times
Millimetre calibration for printers that drift, on both axes
Choose every field: title, SKU, price, vendor, barcode — turn off what you don't want
Currency symbol, position and separators you control (R$ 24,90 or 24,90 €)
Avery, DYMO, Zebra and Pimaco stocks ready to pick
Templates saved and reopened exactly as you left them
```

> A do € existe porque um lojista europeu reclamou disso especificamente. Item
> de lista que nasceu de uma frase real converte melhor que adjetivo.

---

## App card subtitle
*(máx. 62 caracteres — aparece nas listagens)*

```
Barcode labels for shelves, with real calibration
```

---

## Categoria e busca

**Categoria:** Store management → Inventory management
*(alternativa: Selling products → Product display. A primeira é onde o app
oficial está, e é onde o lojista com essa dor procura.)*

**Termos de busca:**
```
barcode labels, product labels, price labels, shelf labels, label printing,
avery labels, zebra printer, zpl, dymo, barcode generator, sku labels
```

---

## Preços
*(o que declarar na aba de pricing)*

| plano | preço | o que declarar |
|---|---|---|
| Free | US$ 0 | 1 template, 100 labels/month, sheet labels (PDF) |
| Pro | US$ 9.99/mês | Unlimited labels and templates, thermal printing (ZPL) |
| Business | US$ 19.99/mês | Everything in Pro, multiple locations, template history |

**7 dias de teste grátis** em ambos os pagos.

> Uma ressalva honesta sobre o Business: ele promete "múltiplos locais e
> histórico de modelos", e **nenhuma das duas coisas está construída**. Ou você
> constrói antes de publicar, ou tira o plano da ficha. Vender o que não existe é
> reprovação na revisão e reclamação depois.

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

- [ ] **Ícone** — 1200×1200px, sem texto dentro
- [ ] **Capturas de tela** — mínimo 3, 1600×900px
- [ ] **Hospedagem fixa** — o endereço do túnel muda e a revisão não sobrevive a isso
- [ ] **Preencher `CONTATO_EMAIL`, `CONTATO_NOME` e `HOSPEDAGEM`** no `.env`,
      senão a política de privacidade vai ao ar dizendo "(preencha …)"
- [ ] **Decidir o plano Business** — construir ou tirar da ficha
- [ ] **`MODO_DEV=0`** em produção, senão o traceback do Flask fica exposto e a
      rota `/dev/` existe

---

## Duas coisas que eu não escreveria na ficha

**Não cite o app oficial.** É tentador — a nota 2,3 é o argumento inteiro. Mas
comparação direta com outro app é motivo de reprovação, e mesmo se passasse,
posiciona você como reação em vez de produto.

**Não venda a impressora térmica como manchete.** Todo caminho do navegador até
uma térmica exige software instalado na máquina do lojista. Prometer isso na capa
atrai justamente quem vai se frustrar antes de imprimir a primeira etiqueta.
Ela está na lista, com a ressalva, e é o lugar certo dela.
