# O screencast

Serve a **duas** coisas, e por isso subiu de prioridade:

1. **Exigência da submissão.** *"Include a screencast to demonstrate your app's
   onboarding and features"*. Sem ele a submissão não completa.
2. **É a única forma de mostrar o app antes de ele existir na vitrine.** Não dá
   pra instalar numa loja sem estar listado (verificado — "instalação por link
   direto" não existe). Então nas [dez conversas](dez-conversas.md) não é
   *"testa aí"*, é *"olha isto funcionando"*.

> **Grave uma vez, corte duas.**
> **Cheio (~3 min)** para a submissão · **curto (~60s)** para as conversas.
> O curto é só um recorte do mesmo arquivo: problema → gera → gravou.

---

## Antes de gravar

**O escopo `write_products` precisa estar ligado**, senão as duas cenas que
mais importam não acontecem — o gerador só mostra a prévia e recusa gravar.
Ver [`roadmap.md`](roadmap.md).

**Grave na loja de desenvolvimento de verdade** (`etik-jks2lorw.myshopify.com`),
dentro do admin da Shopify — não no `/dev/`. O revisor quer ver o app real,
embutido, como o lojista vê.

Checklist:

- [ ] Escopo ligado e app **reinstalado** na loja (escopo novo pede
      consentimento novo)
- [ ] Produtos carregam
- [ ] **Pelo menos 3 produtos sem SKU e sem código de barras** — são eles que
      fazem as cenas 2, 3 e 4 existirem
- [ ] Pelo menos 1 produto **com** código válido (serve de contraste)
- [ ] Abas, notificações e coisa pessoal fora da tela
- [ ] 1920×1080, janela limpa
- [ ] **Sem áudio é aceitável.** O roteiro funciona mudo, porque cada cena
      mostra o resultado na tela

---

## O roteiro

### 1. Entra e já está pronto (0:00–0:12)

Admin → **Apps** → **Etik Barcode Labels**.

O app abre **dentro** do admin com o catálogo carregado. É o "onboarding" que
eles pedem: não há cadastro, não há configuração, não há tela de boas-vindas.

> *"The app opens inside the Shopify admin. Nothing to create, nothing to
> configure — your products are already here."*

### 2. O problema, na tela (0:12–0:28)

Abrir o filtro e escolher **"Sem os dois"**.

A lista encolhe e o app diz **quantos** estão sem, **entre quantos olhou**.
Essa segunda parte é de propósito: dizer "3 sem código" sem dizer "entre os
400 que varri" deixaria o lojista achar que são 3 na loja inteira.

> *"These products have no SKU and no barcode. You can't print a label for
> something that has no number."*

### 3. Gerar os SKUs que faltam (0:28–1:00)

**É aqui que o app passa a resolver o passo zero, e não só o terceiro.**

- Clicar em **Preencher SKUs que faltam**
- Mostrar o **molde** (`{fornecedor}-{tipo}-{variante}`) e trocar uma peça
- **Ver prévia** → a tabela inteira aparece: produto, SKU atual, vai virar
- **Parar sobre uma linha com ⚠** e mostrar que ela ganhou sufixo porque
  repetia outro SKU da loja
- **Desmarcar uma linha** de propósito e mostrar o botão mudando o número
- **Gravar** → a contagem confirma
- **Desfazer o último** → e os produtos voltam

> *"Nothing is written until you see the whole table and click. And you can
> undo it."*

**A cena do desfazer é obrigatória.** É o que separa este app de uma macro de
planilha, e é a pergunta que o revisor vai fazer.

### 4. Gerar os códigos de barras (1:00–1:45)

- Clicar em **Preencher códigos de barras**
- **Abrir o seletor de tipo** e passar pelos três, devagar o suficiente pra ler
  o aviso mudando embaixo:
  - **GTIN-13 do meu prefixo GS1** → aparece o campo de prefixo, e ao digitar
    ele diz **quantos produtos cabem**
  - **Código interno** → *"funciona no seu PDV e no seu estoque, mas não serve
    para vender este produto em outra loja"*
  - **Code 128 a partir do SKU**
- Escolher **código interno**, **Ver prévia**
- Mostrar a coluna **Tipo** dizendo, linha por linha, que número é aquele
- **Gravar**

> *"Three kinds of code, and the app tells you where each one is valid. An
> internal code is not a GTIN, and pretending otherwise would cost the
> merchant later."*

**Esta cena é o diferencial honesto.** Os concorrentes geram código; nenhum
diz ao lojista que faixa de numeração ele está usando.

### 5. Bipar e enfileirar (1:45–2:05)

- Clicar na busca e **digitar um código completo + Enter** (é o que o leitor
  faz)
- O produto entra sozinho, com a quantidade vinda do estoque
- Repetir, pra mostrar que **acumula**

> *"A scanner types and presses Enter. Scan, scan, print."*

### 6. Montar a etiqueta (2:05–2:25)

- Ligar e desligar **título, SKU, preço** — a prévia muda
- Trocar o papel: uma Avery, depois **Medida livre** com largura e altura
  digitadas

> *"The preview is drawn by the same code that writes the printer file."*

### 7. A cena que nenhum concorrente mostra (2:25–2:45)

- Em **Medida livre**, digitar uma largura estreita (**25mm**)
- O código **some** da prévia e o aviso explica **por quê**
- Voltar pra uma largura que cabe, e o código volta

> *"A barcode that wouldn't scan is never printed — and the app says why."*

### 8. Sair com arquivo, e a régua (2:45–3:00)

- **Baixar PDF**, mostrar o arquivo aberto
- Abrir **"A etiqueta está saindo torta?"** e mostrar a régua de calibração

### 9. Planos (3:00–3:10)

**Ver planos** → Grátis e Pro. Responde antecipadamente a pergunta do revisor
sobre cobrança.

---

## O corte de 60 segundos, para as conversas

Mesmo arquivo, só as cenas **2 → 3 → 4**, sem narração:

```
o problema (sem SKU, sem código)  →  gera SKU  →  gera código  →  gravou
```

É o que responde *"o que seu app faz?"* em um minuto. O resto é detalhe que só
interessa a quem já disse sim.

---

## O que NÃO mostrar

- **Nada do `/dev/`.** Não existe em produção e confunde.
- **Nada de terminal, código ou testes.** O revisor avalia o produto.
- **Não acelere o vídeo.** Prévia carregando em velocidade real é prova de que
  ela é rápida; acelerado parece truque.
- **Não mostre gravação falhando.** Se der erro, pare e regrave a cena.

---

## Depois de gravar

O arquivo entra na submissão junto das **instruções de teste**
([`instrucoes-de-teste.md`](instrucoes-de-teste.md)), onde é preciso dizer com
todas as letras:

- não existe conta a criar — o app abre pelo admin da Shopify
- **o app escreve no catálogo, e só depois de o lojista revisar e clicar** — com
  o escopo ligado, esta é a primeira pergunta do revisor
- como o revisor alcança o plano Pro: em loja de desenvolvimento a cobrança do
  Shopify é sempre de teste, então ele instala numa loja dessas e assina
  normalmente. Escreva isso, porque ele não vai adivinhar.
