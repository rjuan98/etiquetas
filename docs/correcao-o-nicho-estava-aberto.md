# A correção: o nicho estava aberto, e a gente nunca entrou

**09/10/2026, à tarde.** De manhã eu disse que a loja de apps não deixava entrar
nesta categoria e recomendei não pagar os US$ 19. **Estava errado.** Isto registra
a medição que me desmentiu.

---

## O erro: uma conclusão em cima de um ponto de dado

De manhã eu olhei o **LabelFast** — gêmeo do Etik, listado desde 06/07/2026,
**zero avaliações** três meses depois — e concluí que a vitrine não entregava
para quem chega novo.

Um ponto. Depois medi dez.

## O instrumento que faltava: a DATA das avaliações

Contagem de avaliações não diz **quando**. Um app com 40 pode ter juntado em três
anos (nicho congelado) ou em seis meses (nicho vivo). O teste certo é olhar
quando a avaliação chegou.

**Nicho de etiquetas, apps minúsculos:**

| app | avaliações | última avaliação |
|---|---|---|
| `labelcraft` | 5 | **out/2026** |
| `inventory-scan` | 4 | **set/2026** |
| `labeldock` | 1 | **set/2026** |
| `label-wizard` | 3 | ago/2026 |
| `airo-sku-barcode-generator` | 39 | jul/2026 |
| `skywalk-sku-generator` | 9 | jun/2026 |
| `barcode-man` | 97 | jun/2026 |
| **`labelfast`** | **0** | **nenhuma** |

Apps com **1, 3, 4 e 5 avaliações** receberam avaliação no último mês. O
LabelFast é a **exceção**, não a regra — e eu generalizei a exceção.

> **Cheio não é fechado.** O nicho tem Delta/RF (539), o oficial (476), Yanet
> (457), EasyScan (373) — e mesmo assim admite entrante novo.

---

## O contra-exemplo que decide: LabelCraft

Entrou por volta de **agosto de 2026** — o mesmo período em que o LabelFast
estava parado em zero — e em dois meses tem 5,0 e está acumulando.

**Cobra US$ 9,99 / 24,99 / 39,99 por mês**, com anual. Ou seja: o mercado paga
mais do que a gente supôs (nosso Pro é US$ 9,99, o piso deles).

**Tem link de "Ver loja de demonstração"** na ficha — o lojista experimenta antes
de instalar.

E os destaques da ficha deles são, linha por linha, as queixas que a gente mapeou:

- **"Gerador de código de barras: GTINs a partir do prefixo da GS1 ou códigos
  internos sem prefixo"**
- "Toda variante começa do zero: nada é impresso até você definir uma quantidade"
- "Trabalhos anteriores são reimpressos com o mesmo layout, mesmo após editar o
  modelo"
- "Etiquetas ilimitadas nos planos Pro: sem limite mensal, créditos ou pacotes"
- "Recebimento: cole uma lista de fornecedor ou crie etiquetas de transferência"

---

## As duas coisas que isto ensina, e doem

### 1. O recurso que a gente decidiu não fazer é a PRIMEIRA linha de quem está crescendo

Ver [`decisao-gerar-codigo.md`](decisao-gerar-codigo.md). A decisão foi "não
gerar código de barras; manter os dois escopos de leitura".

O gatilho que escrevemos para reabrir era: *"um lojista de verdade dizer que não
consegue usar porque os produtos dele não têm código"*.

**Esse gatilho era circular.** Ele exigia lojistas para uma decisão que
determinava se teríamos lojistas. Com zero usuários, ele nunca podia disparar.

O LabelCraft resolve isso de um jeito que a gente não tinha considerado: gera
**GTIN a partir do prefixo GS1 do próprio lojista**, ou **código interno sem
prefixo**. Quem tem prefixo usa o dele; quem não tem recebe código interno. É
honesto e não exige a gente comprar prefixo nenhum.

### 2. O problema do Etik nunca foi a categoria — foi que a gente nunca entrou

O app está pronto, testado e no ar desde agosto, e **nunca foi submetido**. Os
US$ 19 e um screencast separam ele de estar na mesma prateleira onde o LabelCraft
cresceu em dois meses.

---

## O que vale fazer com isso

**A decisão dos US$ 19 volta a valer a pena.** Falta só o screencast; os webhooks
de conformidade já estão declarados e as instruções de teste escritas.

**E o item 5 (gerar código) merece ser reaberto** — não por palpite, mas porque
quem está crescendo usa ele como manchete. O gatilho antigo era circular e deve
ser substituído.

**O que NÃO mudou:** o nicho é cheio, e o realista é virar um app de 10 a 50
avaliações, não liderar. Mas 12 a 50 clientes pagantes sempre foi a meta.
