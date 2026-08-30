# As mensagens, prontas para enviar

Oito lojas que **reclamaram publicamente** do app oficial. Uma mensagem para
cada, escrita para aquela queixa.

> **Regras que não mudam.**
>
> - **Uma por vez, à mão.** Disparar as oito de uma vez é spam, e se parece com
>   spam vira spam. O contato de cada loja se busca na hora de escrever para ela
>   — nunca montar uma lista.
> - **Não prometer o que não existe.** Cada frase abaixo foi conferida contra o
>   código. Onde há ressalva, ela está escrita.
> - **Fácil de ignorar.** Ninguém deve a você uma resposta.

> **Nenhuma destas mensagens leva link de instalação, e isso é de propósito.**
>
> Uma loja de verdade **não instala** um app da Shopify que não passou pela
> revisão — nem mesmo "não listado". Resposta de um funcionário da Shopify:
> *"app review is required […] even if you are leaving the app in an 'unlisted'
> state"*. O link direto só funcionou na loja de **desenvolvimento**.
>
> Então a ordem é: **perguntar primeiro, gastar depois.** Cada mensagem pede um
> "sim" pequeno. Se alguém disser sim, aí valem os US$ 19 da submissão — o
> dinheiro vai atrás de um interessado, não na frente dele.
>
> Ver [`primeiros-lojistas.md`](primeiros-lojistas.md) para as duas rotas de
> distribuição e por que a "custom" (grátis, sem revisão) não serve aqui: ela
> vale para **uma loja só** e é **irreversível**.

---

## 1. Frip'Dream (França) — o € do lado errado

> *"le symbole € est placé à gauche du montant"*

```
Subject: your review of Retail Barcode Labels — the € position

Hi,

I read your review about the € ending up on the left of the amount. That
one stuck with me, because it's not a preference — it's just wrong in
France, and there's no reason a label app should decide it for you.

I've spent the last few months building an alternative. The currency
symbol, which side it sits on, and both separators are yours to set, so
"12,50 €" comes out as "12,50 €".

It works but isn't listed on the App Store yet. Would you be willing to
use it for free and tell me whether it actually solves your problem? No
cost and nothing to commit to — I mainly need to know if it works for
someone who isn't me.
```

---

## 2. The Scented Cardinal (EUA) — preço que não sai da etiqueta

> *"can't remove price for certain labels. My prices fluctuate"*

```
Subject: your review of Retail Barcode Labels — removing the price

Hi,

Your review mentioned you can't take the price off certain labels
because your prices fluctuate. I've been building an alternative to that
app, and every field is a checkbox — price included. Turn it off and it
isn't printed.

Two things worth saying up front: you'd be one of the first stores using
it, and it isn't on the App Store yet.

Would you like to try it for free and tell me if it holds up on a real
catalog? No cost, no commitment.
```

---

## 3. Patch Magazine (Reino Unido) — o modelo que mudou sozinho

> *"all of a sudden my barcodes are longer and a different font"*

```
Subject: your review of Retail Barcode Labels — labels changing on you

Hi,

You wrote that your barcodes suddenly came out longer and in a different
font. That's the complaint that made me start building an alternative,
because a label that changes on its own is worse than one that was never
good: you've already bought the paper.

The output is frozen by tests that compare it byte for byte against a
saved copy. If a change would alter your label, the build fails before it
ever reaches you. That's a promise about how it's built, not a feature.

It's finished but not listed yet. Would you use it for free and tell me
whether it stays put? No cost, nothing to commit to.
```

---

## 4. Boutique Venus (Holanda) — o preço que some sem avisar

> *"price is not visible when there is no space"*

```
Subject: your review of Retail Barcode Labels — the price disappearing

Hi,

Your review said the price isn't visible when there's no space. I've been
building an alternative, and I want to be straight about this one: on a
small label, something still has to give — that part is physics.

What's different is that it tells you. If a field doesn't fit, the app
says which one and why, before you print, instead of quietly dropping it.
And the preview on screen is drawn by the same code that drives the
printer, so what you see is what comes out.

It's not on the App Store yet. Would you try it for free and tell me if
that's actually better in practice? No cost, no commitment.
```

---

## 5. Vintage Dragonfly Boutique (EUA) — o código gigante

> *"labels printing with a HUGE barcode"*

```
Subject: your review of Retail Barcode Labels — the huge barcode

Hi,

You wrote about labels printing with a huge barcode. I've been building
an alternative, and there the barcode is sized from the label itself — it
gets the space it needs to scan and no more, so it can't take over a
small label.

You also see it before you print: the preview is rendered by the same
code that generates the printer file, not by a separate drawing that
might disagree with it.

It's finished but not listed yet. Would you use it for free and tell me
if the labels come out the size you expect? No cost, nothing to commit
to.
```

---

## 6. Saratoga Chocolate Co. (EUA) — o SKU que sumiu da Avery 5167

> SKU sumiu das etiquetas Avery 5167 depois de uma atualização

```
Subject: your review of Retail Barcode Labels — SKU on Avery 5167

Hi,

You wrote that the SKU disappeared from your Avery 5167 labels. I've been
building an alternative, and I added the 5167 specifically because of
reviews like yours.

Being honest about what that label is: 5167 is 1.75" x 0.5", and there
genuinely isn't room for everything. The app fits the product name, SKU,
price and barcode on it — but only if you turn off the digits printed
under the barcode, which is a checkbox. Those digits repeat what the
barcode already carries; your SKU doesn't exist anywhere else on the
label. The point is that you choose, instead of the app choosing for you
and not saying so.

It's not on the App Store yet. Would you try it for free and tell me if
the 5167 comes out right on real paper? No cost, no commitment.
```

---

## 7. THATS-RALLY (Alemanha) — medida de etiqueta travada

> tamanhos de etiqueta não são livres

```
Subject: your review of Retail Barcode Labels — custom label sizes

Hi,

Your review was about not being able to use your own label size. I've
been building an alternative, and you can type the width and height in
millimetres for the labels you already bought — there's a catalogue of
common ones, and "custom size" at the bottom of the list for everything
else.

One thing it does that I haven't seen elsewhere: if the size you enter is
too narrow for a readable barcode, it says so on screen instead of
printing one that runs off the edge.

It's finished but not listed yet. Would you use it for free and tell me
if it handles your sizes? No cost, nothing to commit to.
```

---

## 8. Rill (EUA) — 1"x1" e etiqueta de joia

> 1"x1" e etiqueta de joia não imprimem

**Esta é a que tem ressalva de verdade. Ela não pode sair da mensagem.**

```
Subject: your review of Retail Barcode Labels — 1"x1" and jewelry labels

Hi,

You wrote that 1"x1" and jewelry labels wouldn't print. I've been
building an alternative and both are in it now — but I'd rather tell you
the limit before you spend time on it than after.

Jewelry labels work fully. On 1"x1", a QR code fits, and a normal barcode
does not: a readable EAN-13 needs about 28mm of width and the label is
25.4mm. That's the standard against a ruler, not something I can code
around — no app can. What mine does is say so on screen, instead of
printing a barcode that runs off the edge and won't scan at the register.

If a QR code works for your 1"x1" labels, I'd love for you to try it for
free and tell me how it goes. If it doesn't, that's a fair answer and I
won't take more of your time.
```

---

## Se alguém disser sim

É aí que os US$ 19 fazem sentido, e não antes. A ordem:

1. **Responda rápido**, e diga a verdade: o app está pronto e a submissão leva
   alguns dias. Ninguém se ofende com isso; some quem fica sem resposta.
2. **Submeta o app** — [`ficha-loja-de-apps.md`](ficha-loja-de-apps.md) tem o
   texto todo pronto pra colar, e a lista do que falta preencher.
3. **Avise quando estiver no ar** e mande o link. Essa pessoa é sua primeira
   avaliação, e cinco avaliações dão o selo *Built for Shopify*.

Se ninguém disser sim, você não gastou nada — que é a razão de a pergunta vir
antes do dinheiro.

## Depois de enviar

Anote a data de cada uma. O critério combinado: **duas semanas, cinco
mensagens, nenhuma resposta** → o canal está errado e muda, em vez de insistir e
descobrir tarde.

Uma resposta que instala já muda de patamar: passa a existir um lojista de
verdade usando, que é o que decide se isso vira negócio.
