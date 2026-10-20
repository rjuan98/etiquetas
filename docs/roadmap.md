# O roadmap — e o plano B

**20/10/2026.** Escrito depois de um dia longo, com os dois geradores prontos e
o app ainda sem nenhum cliente pagante.

Este documento responde três perguntas, nesta ordem:

1. O que falta no código
2. **Quando parar** — o critério que impede o Etik de virar poço sem fundo
3. O que fazer se ele não der certo

---

## A inversão: a conversa vem ANTES dos US$ 19

O plano antigo era: terminar → screencast → pagar os US$ 19 → submeter →
esperar ser encontrado. **Essa ordem está errada**, e errada do jeito que já
custou caro duas vezes neste projeto.

Os US$ 19 e a revisão da Shopify são a parte **cara e lenta**. As conversas com
lojista são a parte **barata e rápida**. Fazer o caro primeiro é pagar por uma
informação que a conversa dá de graça.

E tem um detalhe que trava o atalho: **não dá pra instalar o app numa loja de
alguém sem estar listado** (verificado — a ideia de "link direto para instalação
não listada" é falsa). Então a conversa não pode ser *"testa aí"*. Ela tem que
ser *"olha isto funcionando"* — e é exatamente pra isso que serve o screencast.

> **O screencast deixa de ser item de submissão e vira a ferramenta de venda.**
> Ele serve às duas coisas, e é por isso que ele sobe de posição.

```
  terminar o código  →  screencast  →  10 conversas  →  US$ 19  →  submeter
                                            ↑
                                   o portão de verdade
```

---

## 1. O que falta no código

Em ordem, com o custo honesto.

### Antes de commitar

| | o que é | custo |
|---|---|---|
| **a.** | **Testes de rota do gerador de código** — `/api/codigos/previa`, `/aplicar`, `/desfazer`. A seção 78 cobre as rotas de SKU de ponta a ponta; as de código **não têm nada**. É a maior lacuna aberta, e é onde morava o bug de colisão. | horas |
| **b.** | Sabotagens dessas rotas | pouco |
| **c.** | README: as contagens mudaram de novo (1.157 checagens, 111 sabotagens) | minutos |
| **d.** | Uma corrida limpa de `sabotagem.py`, sozinha, do começo ao fim | ~50 min de máquina |

### O passo irreversível: o escopo `write_products`

Isto muda o que é **público**, então vai tudo no mesmo commit:

- `shopify.app.toml` ganha o escopo
- o teste que hoje trava *"nenhum escopo de escrita"* passa a travar o
  contrário: **só** `write_products` entra, e nada de cliente ou pedido
- a política de privacidade muda
- a frase da ficha: *"Read-only: the app never writes to your catalog"* vira
  *"Nothing is written until you review the list and click apply — and you can
  undo it."*
- **reinstalar na loja de testes** (o escopo novo exige novo consentimento)

Depois disso dá pra exercitar gravar e desfazer de verdade — hoje o modo dev
**recusa** a gravação de propósito, porque fingir a parte perigosa é como se
embarca um defeito.

### Limitação conhecida, escrita pra não ser esquecida

A conferência de repetidos só enxerga **o que foi varrido** (50 produtos, até 8
páginas com filtro). Em catálogo grande isso é um pedaço. A tela **diz isso** ao
lojista, que é o mínimo honesto — mas se algum dia houver loja de 5 mil
produtos, isto precisa virar varredura completa antes de gravar.

---

## 2. O critério de parada do Etik

Sem isto, "mais uma feature" dura pra sempre.

> **Portão:** depois do screencast, 10 conversas com lojistas Shopify.
> Se **menos de 3** disserem que pagariam, **não pagar os US$ 19.**

Não é "eles acharam legal". É: *"quanto você paga hoje pra resolver isso?"* e
*"me avisa quando estiver pronto"* — alguém que pede pra ser avisado é sinal;
alguém que elogia não é.

Se o portão fechar, o Etik **não morre**: fica no ar, custa zero, e o motor
inteiro é reaproveitado no plano B abaixo.

---

## 3. O plano B — e por que ele não é "outra ideia"

O erro das duas vezes **não foi a ideia**. A tese — *achar uma brecha num
sistema que já existe* — produziu duas ideias razoáveis. O que falhou foi a
**ordem**: construir antes de perguntar.

Então o plano B não é uma ideia nova. É **a mesma tese com a ordem invertida**.

### O processo, pra valer pra qualquer ideia seguinte

1. **Vitrine com busca** + lacuna medida (a "super balança" já existe)
2. **10 conversas ANTES de qualquer código**
3. Portão: ≥3 dizem que pagariam, ≥1 pede pra ser avisado
4. Só então construir — e **o menor pedaço** que resolve pra essas 10 pessoas
5. Essas 10 são os primeiros clientes **e** as primeiras avaliações

O passo 5 é o pulo do gato: ele resolve o problema de distribuição na raiz, em
vez de torcer pra vitrine entregar. Foi a vitrine que falhou, não o produto.

### O candidato número 1: Nuvemshop

Da pesquisa de 30/08 — a única lacuna de verdade que a super balança achou:

| | |
|---|---|
| lojistas | ~180 mil |
| PDV com leitor de código | sim |
| apps de etiqueta na vitrine | **nenhum** |
| idioma | português |
| quanto do Etik se aproveita | o motor inteiro: ZPL, PDF, SVG, códigos, calibração |

E o melhor: **os lojistas são brasileiros e alcançáveis** — grupo de Facebook,
fórum da própria plataforma, Instagram. As 10 conversas custam zero e levam
dias, não meses. É o oposto do e-mail frio para lojas americanas, que já
falhou e falhou de forma previsível.

**Mas vale a mesma regra:** as 10 conversas vêm antes de portar uma linha.

### Se a Nuvemshop também fechar o portão

Os outros finalistas da pesquisa ficam na fila, e cada um passa pelo mesmo
processo: candidatura por IA, loja pronta pra agente, acessibilidade EU.

E vale dizer em voz alta: **três portões fechados seguidos não seriam azar.**
Seriam sinal de que o alvo (R$ 2–10 mil/mês, quase passivo, de produto próprio)
pede um caminho diferente — e aí a conversa honesta passa a ser sobre vender
trabalho, que é o único caminho com certeza alta.

---

## O que é "quase passivo", medido

Pra não haver surpresa depois: um SaaS B2B a R$ 2–10 mil/mês custa umas **5 a
10 horas por mês**. Suporte, bug, churn, e coisas como o relógio da API que
apareceu hoje (`barcode` vira `barcodes` quando a versão subir).

Pouco. Não zero. E é a coisa mais perto de passivo que se constrói sem capital.
