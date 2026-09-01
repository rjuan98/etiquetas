# Antes de submeter — tudo conferido na fonte

**30/08/2026.** Levantado depois de eu errar **duas** afirmações sobre a loja de
apps no mesmo dia. Tudo abaixo veio da documentação oficial ou de teste contra o
servidor no ar, e está com a frase original quando ela decide alguma coisa.

---

## O dinheiro — e aqui tem notícia boa

| fato | verificado |
|---|---|
| Taxa de submissão | **US$ 19, uma vez por CONTA DE PARCEIRO** — não por app, não por tentativa |
| Fatia da Shopify | **0% do seu primeiro US$ 1.000.000** de receita bruta |
| Acima disso | 15% |
| Processamento | 2,9% sobre a cobrança |

> *"a one-time fee of $19 USD per Partner account"*
> *"100% of your first $1,000,000 USD in gross app revenue"*

Ou seja: na meta de R$ 500–2.000/mês, a Shopify **não fica com nada** além dos
2,9% de processamento. E os US$ 19 valem para sempre, para qualquer app futuro
na mesma conta.

---

## As duas rotas de distribuição

| | revisão | custo | limite |
|---|---|---|---|
| **Pública** (listada **ou não listada**) | **sim** | US$ 19 (uma vez) | nenhum |
| **Custom distribution** | não | zero | **uma loja**, sem cobrança pelo Shopify |

**App "não listado" TAMBÉM passa por revisão.** Isto é o que eu tinha errado.
Resposta de funcionário da Shopify no fórum de desenvolvedores:

> *"app review is required, as the app does need to have a `Public` distribution
> status in order to install it on multiple stores, even if you are leaving the
> app in an 'unlisted' state."*

"Não listado" só controla a **visibilidade na busca**, não dispensa revisão. O
link direto funcionou na loja de **desenvolvimento** porque loja de
desenvolvimento instala app não aprovado.

**E a escolha é definitiva:**

> *"You can't change the distribution method after you select it."*

Escolher *custom* neste app fecha a loja de apps para ele **para sempre**.

---

## O que REPROVA o app

### 1. Webhooks de privacidade não declarados — reprovação explícita

> *"If you don't provide URLs for the mandatory compliance webhooks, or your app
> doesn't respond to these webhooks as required, then your app will be rejected"*

**Este é o item que estava pendente, e ele tinha um defeito de código junto.**

A instalação tentava assinar os três pela API (`webhookSubscriptionCreate`), e
**a API não aceita tópico de conformidade**. As três chamadas falhavam, o erro
era engolido pelo `except`, e ficava a impressão de que estavam ligados.

Nem faria sentido: o `shop/redact` chega **48 horas depois da desinstalação**,
quando o token daquela loja já foi apagado.

Corrigido no código em 30/08/2026 — a instalação assina só `app/uninstalled` e
`app_subscriptions/update`. **Falta a parte que é no painel:**

- [ ] No painel de Partner, em **App setup → Compliance webhooks**, preencher os
      três campos com:
      `https://etikbarcode.pythonanywhere.com/webhooks`
      (a mesma URL nos três — a rota lê o tópico do cabeçalho)

O app **já responde** aos três corretamente, com conferência de HMAC, e isso tem
teste.

### 2. Cobrança fora da plataforma

> *"Apps that use off-platform billing cannot be distributed through the Shopify
> App store"*

**Já está certo:** o app usa Shopify App Pricing (`loja/cobranca.py`).

### 3. App embutido dependendo de cookie de terceiro

> Requisito 1.1.1: *"Your embedded app must function properly without relying on
> third-party cookies or local storage."*

**Já está certo:** o app usa token de sessão, e a razão está escrita em
`web/sessao.py`.

### 4. Screencast — **FALTA**

> *"Include a screencast to demonstrate your app's onboarding and features"*

- [ ] Gravar o vídeo. **O roteiro cena a cena está em
      [`screencast.md`](screencast.md)** — 2 a 3 minutos, gravado na loja de
      desenvolvimento de verdade, não no `/dev/`.

### 5. Instruções de teste — **FALTA**

> *"Include account credentials in your testing instructions"* — e elas precisam
> *"grant full access to the app's complete feature set"*.

- [ ] Escrever as instruções. O app não tem conta própria (a entrada é pelo
      admin do Shopify), então o texto precisa dizer isso e explicar como o
      revisor chega em cada recurso — **incluindo o Pro**, que ele não vai
      conseguir ver sem assinar. Vale oferecer liberar o Pro na loja de teste
      dele, ou explicar como usar a loja de desenvolvimento, onde a cobrança do
      Shopify é sempre de teste.

---

## Conferido contra o servidor no ar, hoje

| checagem | resultado |
|---|---|
| `/dev/` em produção | **404** — `MODO_DEV=0` está certo |
| `/privacy` | no ar, sem espaço em branco por preencher, com contato real |
| `/saude` | `{"ok": true, "configuracao_faltando": []}` |
| token que expira | migrado e funcionando (produtos carregam) |

> **Cuidado com a `/saude`:** ela confere `CHAVE_SEGREDO`, `SHOPIFY_CHAVE_API`,
> `SHOPIFY_SEGREDO` e `APP_URL`. Ela **não** confere os campos de contato da
> política de privacidade. Esses foram verificados na página, à mão.

---

## O risco operacional que ninguém lembra

O PythonAnywhere gratuito **expira o app web periodicamente** — é preciso entrar
e renovar. Se ele cair:

- durante a revisão → o revisor acha um site morto e **reprova**
- depois de publicado → todo lojista instalado vê o app quebrado

- [ ] Colocar lembrete de renovação no calendário **antes** de submeter
- [ ] Com o primeiro cliente pagante, subir para o plano de US$ 5/mês, que não
      expira

Isto não é detalhe: é a diferença entre um app que existe e um que some sozinho.

---

## A ordem que economiza dinheiro

1. **Mandar as mensagens** — [`mensagens.md`](mensagens.md). Custo: zero. Elas
   não levam link, pedem só um "sim".
2. **Se alguém disser sim**, fazer o que falta acima (webhooks no painel,
   screencast, instruções de teste).
3. **Aí pagar os US$ 19** e submeter.
4. **Renovar o PythonAnywhere** e anotar a data.

O dinheiro entra no passo 3, atrás de um interessado — nunca na frente dele.

---

## As duas coisas que eu afirmei errado hoje

Ficam registradas porque o padrão importa mais que os casos:

1. *"App novo precisa de ~10 avaliações em 30 dias ou some do ranking."*
   **Não existe.** A busca da Shopify tem mecanismo que **favorece** app pequeno
   ganhando tração, e o selo *Built for Shopify* pede 5 avaliações.
2. *"App não listado instala em qualquer loja por link direto, então dá pra ter
   os primeiros clientes de graça."* **Não instala** — só loja de
   desenvolvimento.

As duas foram ditas com confiança e sem verificar, e as duas empurravam a mesma
conclusão. Conferir custou quinze minutos.
