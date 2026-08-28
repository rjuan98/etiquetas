# Os primeiros lojistas

Vinte lojas que **reclamaram publicamente** do app oficial, tiradas das
avaliações de uma estrela em `apps.shopify.com/retail-barcode-labels/reviews`.

Cada uma disse o nome da loja e qual é a dor. Nenhuma lista comprada chega perto
disso: são pessoas que usam Shopify, imprimem etiqueta, e estão insatisfeitas a
ponto de escrever sobre isso em público.

> **O contato não está aqui de propósito.** Nome de loja e reclamação são
> públicos na página do app. Sair montando um banco de e-mails transformaria isto
> numa lista de spam — o contato de cada uma você busca na hora de escrever para
> ela, uma por uma.

---

## O padrão que apareceu

**Cinco das vinte reclamam da MESMA coisa**: o app passou a marcar todos os
produtos e a imprimir uma etiqueta de cada por padrão.

> *"The new default to printing one label of every product is a horrible update"*
> — Bhumi Organic Cotton
>
> *"please make the default back to zero without having to click several times"*
> — Golden Hour Gift Co
>
> *"The default to printing 1 label makes no sense & is really slowing me down"*
> — Jenny G's Art Supply
>
> *"Auto check of every product when I go to print just ONE label is a pain"*
> — Indy Home
>
> *"default for printing stickers has changed from zero to one"* — Maiocchi

É a reclamação número um, e é exatamente onde o nosso app é melhor: **nada vem
marcado, e a quantidade vem do estoque.** Isso deveria ser a primeira frase de
qualquer mensagem, e já é a segunda linha da ficha.

---

## Quem escrever primeiro

Ordenado por quanto a nossa resposta é exata. Escrever para quem a gente **não**
resolve queima o contato e é desonesto.

### Nível 1 — a gente resolve exatamente isso

| loja | país | a queixa | o que dizer |
|---|---|---|---|
| **Frip'Dream** | França | *"le symbole € est placé à gauche du montant"* | Símbolo, posição e separadores são escolha sua. Foi construído por causa desta queixa. |
| **The Scented Cardinal** | EUA | *"can't remove price for certain labels. My prices fluctuate"* | Cada campo liga e desliga, inclusive o preço. |
| **Patch Magazine** | Reino Unido | *"all of a sudden my barcodes are longer and a different font"* | Seu modelo não muda sozinho — tem teste que congela a saída byte a byte. |
| **Boutique Venus** | Holanda | *"price is not visible when there is no space"* | Você controla símbolo, espaço e separadores. |
| **Vintage Dragonfly Boutique** | EUA | *"labels printing with a HUGE barcode"* | A altura do código é sua, e a prévia mostra antes de imprimir. |

### Nível 2 — o grupo da quantidade

| loja | país |
|---|---|
| **Bhumi Organic Cotton** | Austrália |
| **Golden Hour Gift Co** | EUA |
| **Jenny G's Art Supply** | EUA |
| **Indy Home** | EUA |
| **Maiocchi** | Austrália |

Todas a mesma frase: nada vem marcado, e a quantidade sai do estoque. Recebeu 40
unidades, são 40 etiquetas.

### Nível 3 — resolve em parte, e vale ser honesto sobre o resto

| loja | país | a queixa | a ressalva |
|---|---|---|---|
| **Saratoga Chocolate Co.** | EUA | SKU sumiu das etiquetas Avery 5167 | O SKU volta, mas **a 5167 não está no nosso catálogo** ainda |
| **THATS-RALLY** | Alemanha | tamanhos de etiqueta não são livres | Temos 11 formatos prontos, mas **não medida livre** |
| **Rill** | EUA | 1"x1" e etiqueta de joia não imprimem | Temos a de joia; **1"x1" não está no catálogo** |

### Não escrever

| loja | por quê |
|---|---|
| Fulkerson Winery and Farm | quer imprimir a partir de Ordem de Compra — **a API do Shopify não expõe isso** |
| Castore Dev 3 | quer app de PDV para a equipe — não é o que a gente é |
| Panda Hobby, shapeshifter, Comprenew | "parou de funcionar" — é reclamação de instabilidade, não de recurso |
| Lasting Impressions, HAUTE MESS BOUTIQUE | reclamam de **suporte**, não do produto |

---

## O molde da mensagem

Curta, honesta, fácil de ignorar. **Escrita à mão, uma por uma** — disparo igual
para vinte pessoas é spam, e se parece com spam vira spam.

```
Assunto: about your review of Retail Barcode Labels

Hi — I read your review about [a queixa exata, nas palavras dela].

I spent the last few months building an alternative, mostly because of
that exact problem. [uma frase dizendo como resolve.]

It's finished but not launched yet. Would you like to use it for free and
tell me if it actually solves it? No cost, no commitment — I'd just like
to know if it works for someone who isn't me.
```

Se ela topar, o link de instalação é este, trocando o domínio da loja:

```
https://etikbarcode.pythonanywhere.com/instalar?shop=LOJA.myshopify.com
```

O app funciona sem estar na loja de apps — foi assim que ele foi instalado na
Etik.

---

## O que a lista ensinou sobre o produto

Duas coisas que **gente com nome** está pedindo e a gente não tem:

- **Medida livre de etiqueta.** THATS-RALLY e Rill esbarram nisso. Hoje há 11
  formatos prontos e nenhum jeito de digitar uma medida.
- **Avery 5167 e 1"x1".** Duas medidas ausentes do catálogo, cada uma ligada a
  um prospecto direto.

As duas são baratas: a segunda é acrescentar linhas ao `formatos.py`, e a
primeira é um formulário de largura e altura que o motor já sabe usar.

Vale fazer **antes** de escrever para o Nível 3 — assim a mensagem deixa de ter
ressalva.

---

## O critério de parar

Se em duas semanas, com cinco mensagens escritas, **nenhuma responder**, o canal
está errado e a gente muda — em vez de insistir e descobrir tarde.

Se uma responder e instalar, já mudou de patamar: passa a existir um lojista de
verdade usando, que é o que decide se isso vira negócio.
