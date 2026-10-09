# O gerador de código — desenho

**09/10/2026.** Escrito depois da medição que mostrou que **os dois apps que
crescem no nicho usam gerar código como manchete**, e o Etik não gera.

Ver [`correcao-o-nicho-estava-aberto.md`](correcao-o-nicho-estava-aberto.md) e
[`decisao-gerar-codigo.md`](decisao-gerar-codigo.md) — este documento **substitui
o gatilho circular** daquela decisão.

---

## A evidência que reabriu isto

| app | lançado | avaliações | primeira linha da ficha |
|---|---|---|---|
| **RF — Gerador código barras** | 24/10/2025 | **539** · 5,0 · *Built for Shopify* | "Geração de códigos de barras com um clique, único ou em lote" |
| **LabelCraft** | 22/06/2026 | 5 · 5,0 | "GTINs a partir do prefixo da GS1 ou códigos internos sem prefixo" |
| **Etik** | — | — | *não gera* |

Três dos cinco destaques do RF são sobre **gerar**, não sobre imprimir. E ele
saiu do zero ao primeiro lugar do nicho em doze meses.

---

## A pergunta que o desenho precisa responder

**Que número a gente escreve no produto do lojista?**

Não existe uma resposta só, e fingir que existe é o erro que este app não comete.
São três situações diferentes, e o lojista precisa saber em qual ele está.

### Caso 1 — o lojista TEM prefixo de empresa GS1

Ele comprou o prefixo (é pago e anual, e é dele). A gente monta um **GTIN-13 de
verdade**:

```
[prefixo da empresa] + [sequência do item] + [dígito verificador]
```

O verificador já existe no código: `codigos.digito_verificador_gs1`, e ele já é
testado para 11, 12 e 13 dígitos.

**Este código vale no mundo todo.** Serve para vender em outro varejista.

### Caso 2 — o lojista NÃO tem prefixo

Aqui está a tentação de mentir, e a gente não vai. A norma GS1 reserva a faixa
que começa em **2** para **circulação restrita** — uso interno de loja.

```
2 + [11 dígitos] + [verificador]
```

**É um EAN-13 válido e bipa em qualquer leitor.** Mas vale **na loja dele**, não
em outro varejista. Isso precisa estar escrito na tela, não enterrado numa ajuda:

> *"Este é um código interno. Ele funciona no seu PDV e no seu estoque, mas não
> serve para vender este produto em outra loja. Para isso é preciso um prefixo
> de empresa da GS1."*

### Caso 3 — ele só quer organizar, e não vende em outro lugar

**Code 128 a partir do SKU.** Não precisa de autoridade de numeração nenhuma,
aceita letra, e bipa. É a opção mais honesta para quem só quer achar produto na
prateleira.

---

## O gerador de SKU, que é mais barato e quase tão pedido

O RF tem isso no segundo destaque. É **formatação de string com regra**, não
tem norma, não tem verificador:

```
{fornecedor}-{tipo}-{opção}-{sequência}      →  ACME-CAM-M-0007
```

Com três escolhas: o molde, o tamanho da sequência, e maiúsculas ou não.

**Custa muito menos que o gerador de código e resolve a metade do problema.**
Ninguém precisa de prefixo GS1 para ter SKU.

---

## As cinco regras que não podem faltar

Sem elas isto vira o defeito que o app existe para não ter.

**1. A prévia vem antes da escrita, sempre.**
O lojista vê a tabela inteira — produto, variante, código que será gravado —
**antes** de qualquer coisa ir para o Shopify. É a mesma regra da prévia da
etiqueta: nada é prometido que não vá acontecer.

**2. Nunca sobrescrever código existente.**
Só preenche o que está **vazio**. Sobrescrever o código de um produto que já
vende em outro varejista é estrago sem volta. Se um dia houver "regravar", é
botão separado, com confirmação separada.

**3. Conferir colisão dentro da loja.**
Dois produtos com o mesmo código bipam o produto errado no caixa — a pior falha
possível, e é a avaliação de uma estrela que o Yanet levou. Antes de gravar,
conferir o catálogo inteiro.

**4. Desfazer.**
Guardar o que foi gravado, com data e lote. Sem desfazer, isto não sobe. Um bug
nosso aqui mexe no catálogo do lojista, não em papel.

**5. Dizer que tipo de código é.**
Caso 1, 2 ou 3 — na tela, antes e depois. Um código interno apresentado como
GTIN é mentira com consequência comercial.

---

## O que isto custa

### O escopo

Precisa de **`write_products`**. Não tem contorno: o PDV do Shopify consulta o
campo *barcode* da variante, e só ele (verificado em 30/08).

### A frase que se perde

A ficha hoje diz **"Read-only: the app never writes to your catalog"** — a única
linha que nenhum concorrente podia escrever.

Ela vira outra coisa, e a nova também é verdadeira e vale:

> *"Nothing is written to your catalog until you review the list and click
> apply — and you can undo it."*

**No MESMO commit** mudam: a política de privacidade, a ficha, o
`shopify.app.toml`, e o teste que hoje trava "nenhum escopo de escrita" — esse
teste passa a travar o contrário, que é *só* `write_products` entrar, e nenhum
de cliente ou pedido.

### O tempo

Não é meio dia. Contar em dias, e contar a revisão mais dura da loja de apps
junto — app que escreve no catálogo é olhado com mais atenção.

---

## O resto da lista, pra bater de frente

Levantado das fichas de quem está na frente, em ordem de **valor ÷ custo**:

| recurso | quem tem | custo | vale? |
|---|---|---|---|
| **Gerar código de barras** | RF, LabelCraft, LabelFast | dias | **sim — é a manchete deles** |
| **Gerar SKU por regra** | RF | horas | **sim, e é barato** |
| **"Mostrar só produtos sem código"** | RF (destaque nº 5) | horas | **sim — o catálogo já está carregado** |
| Reimprimir trabalho anterior com o mesmo layout | LabelCraft | médio | provável — já guardamos impressões, falta a foto do modelo |
| Loja de demonstração na ficha | LabelCraft | baixo (é configuração) | sim, é da ficha |
| Importar CSV | Yanet | médio | depois |
| Mais símbolos (Code 39, Data Matrix) | LabelFast | baixo | **não** — é número pra tabela |
| Integração POS/Stocky | Yanet | alto | não agora |

**O que o Etik já tem e eles não dizem ter:** régua de calibração, prévia gerada
pelo mesmo código da impressora, recusa de código que não bipa (verificador,
largura, zona muda), e medida livre em milímetro.

Isso continua valendo — só não é o que abre a porta. **Abre a porta o gerador; o
resto é o que faz ficar.**

---

## A ordem

1. **Gerar SKU** — mais barato, sem norma, sem risco de mentir
2. **"Produtos sem código"** — horas, e é destaque de ficha
3. **Gerar código de barras**, com as cinco regras acima
4. **Screencast**
5. **Aí sim os US$ 19**

Entrar com o que o mercado compra, e não com o que a gente achou bonito.
