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
| **Vintage Dragonfly Boutique** | EUA | *"labels printing with a HUGE barcode"* | O código é dimensionado a partir da etiqueta — ganha o que precisa pra bipar e nada além. E a prévia mostra antes de imprimir. |

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

### Nível 3 — eram "resolve em parte", e deixaram de ser

As três ressalvas foram construídas em **30/08/2026**, justamente porque cada
uma tinha nome e sobrenome.

| loja | país | a queixa | o que dizer |
|---|---|---|---|
| **Saratoga Chocolate Co.** | EUA | SKU sumiu das etiquetas Avery 5167 | A 5167 está no catálogo, e os quatro campos cabem nela — título, SKU, preço e código. |
| **THATS-RALLY** | Alemanha | tamanhos de etiqueta não são livres | Dá pra digitar largura e altura da etiqueta que você já comprou. |
| **Rill** | EUA | 1"x1" e etiqueta de joia não imprimem | As duas estão no catálogo. **Com a ressalva abaixo.** |

> **A ressalva honesta do 1"×1".** Nessa etiqueta cabe **QR**, e não cabe código
> de barras linear: um EAN-13 legível precisa de 28,3mm de largura e o papel tem
> 25,4mm. Isso é a norma contra a régua, não limitação do app — e nenhum
> concorrente resolve, porque não tem como. O app **diz isso na tela** em vez de
> imprimir um código serrado pela borda.
>
> Escrever pra Rill sem essa frase seria vender o que a gente não entrega.

### Não escrever

| loja | por quê |
|---|---|
| Fulkerson Winery and Farm | quer imprimir a partir de Ordem de Compra — **a API do Shopify não expõe isso** |
| Castore Dev 3 | quer app de PDV para a equipe — não é o que a gente é |
| Panda Hobby, shapeshifter, Comprenew | "parou de funcionar" — é reclamação de instabilidade, não de recurso |
| Lasting Impressions, HAUTE MESS BOUTIQUE | reclamam de **suporte**, não do produto |

---

> **Uma promessa que estava errada aqui.** A versão anterior desta linha dizia
> *"a altura do código é sua"*. Não é: o lojista não escolhe a altura do código,
> ela é calculada a partir da etiqueta (10,4mm numa 2x1, 21,3mm numa 3x2).
> Conferido contra o código antes de escrever a mensagem — que é a razão de
> conferir antes.

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

### A descoberta que encolheu este canal (31/08/2026)

**A Shopify não expõe a loja de quem avalia.** Os nomes nas avaliações são texto
puro, não link — sobra nome e país, e mais nada. Achar o contato depende de a
loja ter presença pública por conta própria.

O placar real das cinco primeiras tentativas:

| loja | achei contato? | por quê |
|---|---|---|
| Patch Magazine | **sim** | é revista, tem presença pública |
| THATS-RALLY | **sim** | é GmbH — a lei alemã obriga Impressum com e-mail |
| Bhumi Organic Cotton | **sim** | marca com lojas físicas |
| Maiocchi | **sim** | idem |
| Saratoga Chocolate | site sim, **e-mail não** | só telefone e endereço |
| Frip'Dream | **não** | nem site nem Instagram |
| The Scented Cardinal | **não** | idem |

**O padrão:** marca estabelecida com loja física é encontrável; loja pequena
só-online não é. E isso **joga a favor** — quem tem loja física é exatamente
quem imprime etiqueta de prateleira.

**O que isso faz com a conta:** o plano era 8 mensagens × 10–30% = 1 a 2
respostas esperadas. Com ~4 alcançáveis, a expectativa cai para 0,4 a 1,2. Ainda
vale mandar, mas **este canal sozinho provavelmente não produz o sinal** que
justificaria adiar a submissão.

### Não mande link de instalação junto

**Corrigido em 30/08/2026, e a versão anterior deste documento estava errada.**

Aqui dizia que bastava mandar `…/instalar?shop=LOJA.myshopify.com` porque "app
não listado instala em qualquer loja". **Não instala.** Resposta de um
funcionário da Shopify, no fórum de desenvolvedores:

> *"app review is required, as the app does need to have a `Public` distribution
> status in order to install it on multiple stores, even if you are leaving the
> app in an 'unlisted' state."*

O link direto funcionou na **loja de desenvolvimento** porque loja de
desenvolvimento instala app não aprovado. Loja de verdade, não.

As opções reais são duas:

| caminho | revisão | custo | limite |
|---|---|---|---|
| **Público** (listado ou não) | sim | US$ 19, uma vez | nenhum |
| **Custom distribution** | não | zero | **uma loja só**, sem cobrança pelo Shopify, e **irreversível** |

O "irreversível" é literal: *"You can't change the distribution method after you
select it."* Escolher custom neste app fecha a porta da loja de apps para
sempre — daria pra criar um segundo app só pro piloto, mas isso é outro conjunto
de credenciais.

**Por isso a mensagem pergunta antes e não manda link.** Se a pessoa responder
que topa, aí sim vale gastar os US$ 19 — o dinheiro vai atrás de um sim, não na
frente dele.

---

## O que a lista ensinou sobre o produto

Duas coisas que **gente com nome** estava pedindo, feitas em 30/08/2026:

- **Medida livre de etiqueta** — THATS-RALLY e Rill. São 13 formatos prontos e,
  no fim da lista, "medida livre" com dois campos em milímetro.
- **Avery 5167 e 1"×1"** — Saratoga e Rill. As duas entraram no catálogo.

E a lista pagou um dividendo que ninguém pediu: **acrescentar o 1"×1" revelou
que o app não conferia se o código de barras cabia na LARGURA da etiqueta.**
Nenhum formato do catálogo esbarrava nisso, então o defeito estava invisível — e
a medida livre teria deixado qualquer lojista digitar 20mm e receber um código
serrado pela borda. Exatamente o defeito que o app existe pra corrigir.

Foi consertado antes da medida livre existir.

---

## As mensagens

Escritas, uma por loja, em [`mensagens.md`](mensagens.md) — as cinco do Nível 1
e as três do Nível 3.

## O critério de parar

Se em duas semanas, com cinco mensagens escritas, **nenhuma responder**, o canal
está errado e a gente muda — em vez de insistir e descobrir tarde.

Se uma responder e instalar, já mudou de patamar: passa a existir um lojista de
verdade usando, que é o que decide se isso vira negócio.
