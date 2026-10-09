# Decisão: o app não gera código de barras (por enquanto)

> ## REABERTA EM 09/10/2026 — e o gatilho abaixo era CIRCULAR
>
> O gatilho escrito aqui era *"um lojista de verdade dizer que não consegue usar
> porque os produtos dele não têm código"*. **Ele exigia lojistas para uma
> decisão que determinava se haveria lojistas.** Com zero usuários, nunca podia
> disparar.
>
> A evidência que o substituiu: **os dois apps que crescem no nicho usam gerar
> código como MANCHETE.** O *RF — Gerador código barras* saiu do zero a 539
> avaliações em doze meses (lançado 24/10/2025) com três dos cinco destaques
> sobre gerar; o *LabelCraft* abre a ficha com "GTINs a partir do prefixo GS1 ou
> códigos internos sem prefixo".
>
> **O desenho está em [`gerador-de-codigo.md`](gerador-de-codigo.md).**
>
> O raciocínio abaixo fica como registro — ele estava bem construído e mesmo
> assim levou ao lugar errado, porque o teste que ele propunha não era
> executável.

**30/08/2026.** Item 5 de [`comparacao.md`](comparacao.md) — o único recurso que
hoje **impede** um lojista de usar o Etik.

---

## O que está em jogo

Os dois concorrentes geram SKU e código de barras para produtos que não têm. O
Etik não. Um lojista com 300 produtos sem código vê "sem código" na lista e não
consegue fazer nada com eles.

E não é um recurso lateral: é o passo **zero** de quem está montando estoque —
*não tenho código → gero → imprimo*. A gente só entra no terceiro passo.

## Não existe caminho do meio, e isso foi verificado

A pergunta que decidiria a forma era: *o PDV do Shopify encontra o produto se a
gente imprimir o SKU como código de barras?*

**Não.** O leitor do Shopify POS consulta o campo **código de barras**, e só ele.
A própria documentação de solução de problemas manda conferir se o número está
no campo *Barcode* e não no *SKU*.

Ou seja: para o produto ser encontrado no caixa, o código **precisa ser gravado
no Shopify**. Ou o app pede permissão de escrita, ou o recurso não existe.

## A decisão

**Não construir agora. Esperar o primeiro lojista pedir.**

Quatro razões, em ordem de peso:

**1. O erro caro deste projeto foi construir por inferência.** O mapa do mercado
e a lista de diferenciais saíram de avaliações lidas, nunca de gente. Ver
[`quem-mais-esta-aqui.md`](quem-mais-esta-aqui.md). Gastar vários dias e o escopo
de escrita para um público de **zero usuários** repete isso com aposta maior.

**2. O custo é assimétrico.** Construir e ninguém vir custa os dias **mais** a
única frase que a concorrência não pode escrever. Não construir e alguém pedir
não custa nada — constrói-se ali, com um lojista real esperando.

**3. "Read-only" vale hoje e é de graça hoje.** Os dois concorrentes pedem
escrita porque geram código. Abrir mão disso quando houver motivo, não por
antecipação.

**4. O risco é de outra natureza.** Etiqueta errada gasta papel. Código errado
**gravado** corrompe o catálogo, e o lojista pode não perceber por semanas. É o
único lugar do app onde um defeito nosso não tem volta para ele.

## O gatilho, escrito para não virar discussão de novo

> **Um lojista de verdade dizer que não consegue usar o app porque os produtos
> dele não têm código de barras.**

Não é "eu achar que seria bom". Não é "o concorrente tem". É uma pessoa, com
loja, dizendo a frase.

As oito mensagens de [`mensagens.md`](mensagens.md) são o caminho mais curto até
esse sinal. E a ficha da loja de apps **já diz** que o app não escreve no
catálogo — então quem precisa disso ou pula, ou escreve dizendo. Silêncio vira
sinal.

## A fraqueza desta decisão, dita em voz alta

Se a falta do recurso for o motivo de ninguém adotar, **o silêncio não conta
isso**. É o ponto fraco real, e o que o reduz é a ficha ser explícita — o que já
é.

## O que fazer quando o gatilho vier

Levantado agora para não ter que redescobrir depois:

- **Escopo:** acrescentar `write_products`. Muda a política de privacidade e
  quebra o teste "nenhum escopo de cliente, pedido ou escrita" — de propósito, e
  no mesmo commit.
- **A frase da ficha muda:** de *"Read-only: the app never writes to your
  catalog"* para algo como *"nothing is written until you click apply"*, que é o
  que o LabelFast anuncia.
- **Faixa de numeração:** EAN-13 começando com **2** é a faixa de circulação
  restrita, reservada a uso interno de loja. Não exige prefixo GS1 comprado. O
  lojista precisa ser avisado de que o código vale na loja dele, **não** em
  outro varejista.
- **O que mais tem que existir:** checagem de colisão dentro da loja, aplicar em
  lote, e desfazer. Sem desfazer, isto não sobe.
- **Postura:** o app **nunca** escreve sozinho. Gera, mostra, e grava quando o
  lojista mandar.
- **Não é meio dia de trabalho.** Contar dias, não horas, e contar a revisão
  mais dura da loja de apps junto.

---

*Esta decisão é reversível e barata de reverter. O que ela evita é construir
antes de saber — que é exatamente o que este projeto já pagou caro para
aprender.*
