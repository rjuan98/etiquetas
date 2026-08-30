# O que eles têm que a gente não tem

Levantado em **30/08/2026** contra as fichas publicadas do *Yanet Retail Barcode
Labels* (4,9 · 448 avaliações) e do *LabelFast* (lançado 06/07/2026), e contra o
nosso próprio código — não de memória.

---

## O que BLOQUEIA um lojista de usar o Etik

Só tem um item nesta lista, e é o mais importante do documento.

### Gerar SKU e código de barras que faltam

> **DECIDIDO em 30/08/2026: não construir agora, esperar o primeiro lojista
> pedir.** O gatilho, as razões e o que fazer quando ele vier estão em
> [`decisao-gerar-codigo.md`](decisao-gerar-codigo.md).

Os dois concorrentes fazem. A gente não.

Um lojista que tem 300 produtos sem código de barras cadastrado **não consegue
fazer nada** com o Etik nesses produtos — a tela mostra "sem código" e acabou.
Isso aparece no nosso próprio catálogo de demonstração.

E não é um recurso à parte: é o passo ZERO de quem está montando o estoque. A
sequência real é *"não tenho código → gero → imprimo"*. A gente entra só no
terceiro passo.

> **Mas isto custa uma promessa.** O app hoje pede **dois escopos, os dois de
> leitura** (`read_products`, `read_inventory`). Gerar código exige
> `write_products` — escrever no catálogo do lojista.
>
> Isso está na política de privacidade, e tem teste travando: *"nenhum escopo de
> cliente, pedido ou escrita"*.
>
> Não dá para contornar imprimindo um código sem gravar: código que não está no
> Shopify não bipa nada no caixa. Ou grava, ou o recurso não serve.
>
> **É uma decisão do Matheus, não uma tarefa de código.**

---

## O que eles têm e a gente não — sem bloquear

| | Yanet | LabelFast | Etik |
|---|---|---|---|
| imprimir a partir de **recebimento de estoque** | — | **sim** | não |
| imprimir a partir de **leitura de scanner** | sim | sim | **sim** |
| **CSV** para impressão em massa | sim | — | não |
| **logo / imagem** na etiqueta | sim | sim (US$ 29,99) | não |
| símbolos de código | 4 | **8**² | 4 |
| idiomas | **6** | 1 | 2 |
| vários **locais de estoque** | sim | sim (US$ 29,99) | não |
| **POS / Flow / Stocky** | sim | — | não |
| campos personalizados (metafields) | — | sim (US$ 29,99) | não |

² eles somam ITF-14, Code 39 e Data Matrix. ITF-14 é o de caixa de atacado, e é
o único dos três que muda a vida de alguém.

---

## O que A GENTE tem e eles não

Isto importa tanto quanto a lista de cima, e é onde a defesa é real.

**Régua de calibração.** Nenhum dos dois menciona. É a resposta exata para
*"as etiquetas saem tortas"* e *"não batem com a medida"* — que é literalmente a
avaliação de 2 estrelas do Yanet:

> *"Brother labels don't match dimensions in app; barcodes look nothing like
> preview"* — ASHER GOODS Co.

**A prévia é gerada pelo mesmo código que gera o arquivo da impressora.** Os dois
anunciam "prévia ao vivo". A nossa tem teste comparando linha por linha o texto
do SVG com o do ZPL — não é a mesma afirmação.

**Código inválido não é impresso.** O dígito verificador é conferido antes. É a
resposta à outra avaliação ruim do Yanet:

> *"It shows invalid GTIN. When we scan barcodes it shows different products"* —
> Anshi Online Jewelry

**Código que não cabe na largura não é impresso** — ele avisa em vez de sair
serrado pela borda. Ninguém mais fala nisso porque quase ninguém confere.

**Ilimitado por US$ 9,99.** O Yanet cobra **US$ 29,99** por 25.000 etiquetas.
Para quem imprime muito, a gente é 3× mais barato. Isso é vantagem de página de
preço, que é onde a comparação acontece.

**Só leitura.** Dois escopos, nenhum de escrita. Hoje é uma promessa forte de
privacidade — e é exatamente o que o item bloqueante acima pede para abrir mão.

---

## O que eu faria, nesta ordem

**1. Grátis de 100 → 200 etiquetas.** Não é recurso, é um número. Perder na
comparação de plano grátis por 2× é a coisa mais barata de consertar no
documento inteiro.

**2. Dizer o que já existe.** A régua de calibração, a prévia fiel e a recusa de
código inválido **não estão na ficha**. É trabalho de texto, não de código, e é o
único lugar onde a gente já ganha dos dois.

**3. ITF-14.** Um símbolo, útil de verdade (caixa de atacado), barato: o
reportlab desenha e o ZPL tem comando. Os outros dois (Code 39, Data Matrix) são
número para a tabela.

**4. Dizer que funciona com leitor.** Já funciona. Ninguém sabe.

**5. Decidir sobre `write_products`.** — **decidido**, ver
[`decisao-gerar-codigo.md`](decisao-gerar-codigo.md). É a única coisa aqui que muda o tamanho do
público — e a única que custa uma promessa. Não fazer é uma resposta legítima:
"este app só lê seu catálogo" é uma frase que nenhum concorrente pode dizer.

Os itens 1, 2 e 4 não são código. O 3 é meio dia. O 5 é uma conversa.

---

## Feito em 30/08/2026

**Item 1** — o grátis passou de 100 para **200 etiquetas/mês**, empatando com os
dois.

**Item 3** — **ITF-14** entrou. Fazer isso encontrou duas coisas:

- **UPC-A com dígito verificador errado passava e ia pro papel.** A conferência
  estava escrita `if simbologia is EAN13`. Código errado imprime bonito, bipa, e
  traz o **produto errado** no caixa — a pior falha possível aqui, porque
  ninguém desconfia dela. É a avaliação de uma estrela que o Yanet levou.
- **O código sumia da prévia sem dizer por quê.** Os motores recusam desenhar
  código que não bipa, e isso está certo; sumir calado não está. Agora a prévia
  explica: *"o código não aparece porque o ITF14 precisa de 14 dígitos, e veio
  com 13"*. O buraco era anterior ao ITF-14 — um EAN-13 com verificador errado
  já sumia calado — mas o ITF-14 recusa todo código de 13 dígitos, então virou
  rotina.

**Itens 2 e 4** — a ficha foi reescrita. As três coisas que só este app faz
subiram para o topo da lista de recursos e entraram no parágrafo de descrição;
antes estavam enterradas ou ausentes. O leitor de código foi **medido antes de
ser escrito**: ele acha o produto certo, mas não marca sozinho — a frase para em
"ready to print" e não promete o clique que ainda existe.

E a ficha ganhou teste. Ela promete número (200 etiquetas, US$ 9,99), nome de
app, lista de simbologias e "read-only" — tudo isso agora é conferido contra o
código, e a sabotagem prova que a conferência funciona. Foi o erro de hoje que
motivou: o documento de prospectos prometia *"a altura do código é sua"*, e o
lojista não escolhe a altura do código.

**O leitor virou fluxo de verdade.** Bipar um código escolhe o produto com a
quantidade do estoque e deixa a busca pronta pro bipe seguinte — bipar, bipar,
bipar, imprimir. Deixou de ser "parcial" na tabela acima.

E construir isso encontrou um defeito antigo e sério: **a fila de impressão
perdia o que tinha sido escolhido em buscas anteriores.** Escolher um produto,
buscar outra coisa e escolher o segundo dava contador dizendo *"2 produto(s), 52
etiqueta(s)"* e PDF com **um** produto. Silencioso, e no momento exato de
imprimir. Atingia qualquer pessoa que buscasse duas vezes — que é como se usa
uma caixa de busca. O leitor teria multiplicado isso, porque bipar é buscar.

**Item 5** — decidido: **não construir agora**. Não existe caminho do meio (o
PDV do Shopify bipa só o campo de código de barras, nunca o SKU — verificado), o
custo é assimétrico com zero usuários, e "read-only" vale hoje e é de graça hoje.
O gatilho é um lojista real dizendo que não consegue usar o app por causa disso.
Ver [`decisao-gerar-codigo.md`](decisao-gerar-codigo.md).

**O plano de `comparacao.md` está fechado.** O que falta não é código: é a
primeira mensagem.
