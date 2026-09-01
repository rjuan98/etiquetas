# O screencast da submissão

**Exigido pela Shopify:** *"Include a screencast to demonstrate your app's
onboarding and features"*. Sem ele a submissão não completa.

---

## Antes de gravar

**Grave na loja de desenvolvimento de verdade** (`etik-jks2lorw.myshopify.com`),
dentro do admin da Shopify — não no `/dev/`. O revisor quer ver o app real,
embutido, como o lojista vê.

Checklist de preparação:

- [ ] Abrir o app na loja e confirmar que **os produtos carregam** (depois da
      migração de token, carregam)
- [ ] Ter pelo menos **um produto com código de barras válido** e, se possível,
      **um sem código** — o segundo serve para uma das cenas
- [ ] Fechar abas, notificações e qualquer coisa pessoal na tela
- [ ] Gravar em **1920×1080**, janela do navegador limpa
- [ ] **Sem áudio é aceitável.** Se preferir narrar, narre; se não, o roteiro
      abaixo funciona mudo, porque cada cena mostra o resultado na tela

**Duração alvo: 2 a 3 minutos.** Mais que isso ninguém assiste até o fim.

---

## O roteiro, cena a cena

### 1. Entrada (0:00–0:15)

Admin da Shopify → **Apps** → **Etik Barcode Labels**.

Mostra o app abrindo **dentro** do admin, com o catálogo já carregado. É o
"onboarding" que eles pedem: não há cadastro, não há configuração, não há tela
de boas-vindas. Instalou, abriu, está pronto.

> Se narrar: *"The app opens inside the Shopify admin. There's no account to
> create and nothing to configure — your products are already there."*

### 2. Escolher produtos, e a quantidade que vem do estoque (0:15–0:45)

- Marcar **dois ou três produtos** na lista
- **Parar de propósito** sobre a coluna de quantidade e mostrar que ela veio
  preenchida com o estoque
- Mudar uma quantidade à mão, para mostrar que é editável

> *"Nothing is pre-selected, and quantities come from stock on hand."*

### 3. O leitor de código (0:45–1:05)

- Clicar na busca e **digitar um código de barras completo + Enter** (é
  exatamente o que um leitor faz)
- Mostrar o produto sendo **escolhido sozinho**, com a quantidade certa
- Repetir com um segundo código, para mostrar que **acumula**

> *"A barcode scanner types and presses Enter, so scanning queues the product
> with the quantity from stock. Scan, scan, print."*

### 4. Montar a etiqueta e a prévia (1:05–1:45)

- Ligar e desligar campos (**título, SKU, preço**) e mostrar a prévia mudando
- Trocar o **formato do papel** — escolher uma Avery e depois **Medida livre**,
  digitando largura e altura
- Mostrar a medida embaixo da prévia acompanhando

> *"The preview is drawn by the same code that writes the printer file."*

### 5. A cena que vende o app (1:45–2:10)

**Esta é a mais importante, e é a que nenhum concorrente mostra.**

- Escolher **Medida livre** e digitar uma largura estreita (por exemplo **25mm**)
- O código de barras **some da prévia**, e o aviso aparece explicando por quê
- Voltar para uma largura que cabe, e o código volta

Alternativa (ou complemento), se houver produto com código inválido: trocar a
simbologia para **ITF-14** num produto de 13 dígitos e mostrar a frase
*"the barcode is not shown because..."*.

> *"A barcode that wouldn't scan is never printed — and the app says why."*

### 6. Sair com arquivo (2:10–2:30)

- Clicar em **Baixar PDF** e mostrar o arquivo aberto, com as etiquetas
- Abrir a seção **"A etiqueta está saindo torta?"** e mostrar a régua de
  calibração e os campos em milímetro

> *"And if your printer drifts, print the ruler, measure it, type the
> difference."*

### 7. Planos (2:30–2:45)

- Clicar em **Ver planos** e mostrar a tela com Grátis e Pro

Isso responde antecipadamente a pergunta do revisor sobre cobrança: ela passa
pelo Shopify App Pricing, que é exigência da loja.

---

## O que NÃO mostrar

- **Nada do `/dev/`.** Ele não existe em produção e mostrá-lo confunde.
- **Nada de terminal, código ou testes.** O revisor avalia o produto.
- **Não acelere o vídeo.** Prévia carregando em velocidade real é prova de que
  ela é rápida; vídeo acelerado esconde isso e parece truque.

---

## Depois de gravar

O arquivo entra na submissão junto das **instruções de teste**. Nelas é preciso
dizer, com todas as letras:

> não existe conta a criar — o app abre pelo admin da Shopify

e explicar **como o revisor alcança o plano Pro**, que ele não vê sem assinar.
Em loja de desenvolvimento a cobrança do Shopify é sempre de teste, então o
caminho é ele instalar numa loja de desenvolvimento e assinar normalmente — vale
escrever isso na instrução, porque o revisor não vai adivinhar.
