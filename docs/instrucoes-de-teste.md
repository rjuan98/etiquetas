# Instruções de teste, para colar na submissão

**Exigência da Shopify:** *"Include account credentials in your testing
instructions"*, e elas precisam *"grant full access to the app's complete feature
set"*.

O app **não tem conta própria** — a entrada é pelo admin da Shopify. Então o
texto abaixo diz isso com todas as letras e, principalmente, resolve os **dois
pontos onde o revisor travaria** e reprovaria achando que o app está quebrado.

---

## Os dois riscos que este texto existe para evitar

**1. Loja de teste sem código de barras nos produtos.** O app lê o campo
*barcode* das variantes. Loja de desenvolvimento recém-criada costuma ter
produtos de exemplo **sem** esse campo preenchido — e aí a lista mostra "no
barcode" em tudo e a etiqueta sai sem código. Um revisor apressado conclui que o
app não funciona.

> Isto é consequência direta da decisão de **não gerar código de barras**
> (ver [`decisao-gerar-codigo.md`](decisao-gerar-codigo.md)). A decisão continua
> certa, mas ela **cobra este preço na revisão**, e o preço se paga escrevendo
> uma frase.

**2. O plano Pro.** O revisor não vê impressão térmica nem modelos ilimitados
sem assinar. Em loja de desenvolvimento a cobrança do Shopify é sempre de teste,
então ele pode assinar sem pagar nada — mas **não vai adivinhar isso**.

---

## O texto (em inglês, para colar)

```
HOW TO ACCESS THE APP

There is no account to create and no credentials to enter. The app is
embedded in the Shopify admin: install it on a development store and open
it from Apps → Etik Barcode Labels. Everything below happens inside that
screen.

BEFORE YOU START — please set one barcode

The app reads the "Barcode" field on product variants. Development stores
often ship with sample products that have this field empty, and in that
case the product list will correctly show "no barcode" for every row.

To see the app work, please open any product in Products → (product) →
Variants, and set the Barcode field to a valid EAN-13, for example:

    7891234567895

One product is enough. The app deliberately does not generate or write
barcodes: it only requests read_products and read_inventory, and never
writes to the merchant's catalog.

WHAT TO TRY

1. Select products. Nothing is pre-selected, and the quantity column is
   filled from inventory on hand.

2. Scan-to-queue. Type a full barcode into the search box and press
   Enter — this is exactly what a barcode scanner does. The matching
   product is queued with the quantity from stock, and the search text
   stays selected so the next scan replaces it.

3. Build the label. Toggle fields (title, SKU, price, vendor, barcode) and
   watch the preview. The preview is rendered server-side by the same code
   that generates the printer file.

4. See the app refuse an unscannable barcode. Choose "Custom size" at the
   bottom of the paper list and enter a width of 25 mm. The barcode
   disappears from the preview and the app explains why: a readable EAN-13
   needs about 28 mm and will not fit. Set the width back to 50 mm and it
   returns.

   You can also set the symbology to ITF-14 on a product whose barcode has
   13 digits, and the app will say the code needs 14.

5. Download. "Download PDF" produces sheet labels. "Thermal printer (ZPL)"
   is a Pro feature — see below.

6. Calibration. Open "Is the label printing crooked?" to print a ruler and
   enter a millimetre offset on both axes.

HOW TO REACH THE PRO PLAN

Free covers 1 template, 200 labels a month, and PDF output. Thermal
printing (ZPL) and unlimited templates and labels are on Pro (US$ 9.99/mo,
7-day trial).

Charges go through Shopify App Pricing. On a development store all charges
are test charges, so you can click "See plans" → Pro and approve the
subscription without being billed. That unlocks the ZPL download and
removes the template limit.

If you would rather not create a subscription at all, tell me the store
domain and I will enable Pro on it manually for the review.

PRIVACY AND SCOPES

The app requests exactly two scopes, both read-only: read_products and
read_inventory. It stores the shop domain, the encrypted access and
refresh tokens, the label templates the merchant designs, and a monthly
count of labels printed. It never reads or stores customer or order data.

Privacy policy: https://etikbarcode.pythonanywhere.com/privacy
Compliance webhooks: https://etikbarcode.pythonanywhere.com/webhooks
(the same endpoint serves all three mandatory topics; it reads the topic
from the X-Shopify-Topic header and verifies the HMAC on every request)
```

---

## Uma observação para o dia da submissão

O item 4 é o que mais convence, e é o que nenhum concorrente escreve numa
instrução de teste. Vale ele estar **numerado e explícito** assim: o revisor tem
minutos por app, e um passo que dá para reproduzir em dez segundos é melhor que
qualquer adjetivo na ficha.

A frase sobre liberar o Pro manualmente é oferta real — se ele pedir, dá para
marcar o plano no banco pela loja dele.
