# Onde estamos

> ## ATENÇÃO: o veredito de 09/10 pela MANHÃ foi CORRIGIDO na mesma tarde.
> Ver [`correcao-o-nicho-estava-aberto.md`](correcao-o-nicho-estava-aberto.md)
> — o nicho ADMITE entrante novo, e o LabelFast era a exceção, não a regra.
> O texto abaixo fica como registro do raciocínio errado.
>
> ## ~~PARADO EM 09/10/2026~~ — e a razão está medida
>
> **O canal da loja de apps não entrega para quem chega novo nesta categoria.**
> Quem provou isso não fomos nós: foi o **LabelFast**, um app com a mesma ideia,
> feito por uma empresa, **listado desde 06/07/2026** — e com **zero avaliações
> três meses depois**. No mesmo período o incumbente Yanet foi de 448 para 457
> avaliações e ganhou o selo *Built for Shopify*.
>
> Ou seja: **estar na vitrine não é ser encontrado.** O experimento que custaria
> US$ 19 já rodou de graça, feito por outro, e o resultado está acima.
>
> O canal de e-mail frio também morreu, e dentro do previsto: das 8 lojas da
> lista só ~4 eram alcançáveis, 3 mensagens foram enviadas em 30–31/08, e a
> expectativa calculada era de 0,4 a 1,2 resposta. Vieram zero (a única resposta
> foi um bot da Bhumi, em um minuto).
>
> **Decisão: não pagar os US$ 19 e não submeter.** O app continua no ar, custa
> zero, e nada se perde ao deixá-lo existir.
>
> O que sobra de vivo da pesquisa está em
> [`../../Hercules/PESQUISA-PLATAFORMAS.md`] — a Nuvemshop é a única lacuna
> medida (180 mil lojistas, PDV com leitor, nenhum app de etiqueta). Mas lá vale
> a mesma regra nova: **antes de portar, confirmar que alguém quer.**


**Atualizado em 30/08/2026.** Documento vivo: estado atual e próxima ação. Se
divergir dos outros documentos, este está mais novo.

---

## O plano, em 09/10/2026 — e onde ele está em 20/10

| | estado |
|---|---|
| 1. **Gerar SKU** por regra | **pronto** — `etiquetas/skus.py`, com prévia, aplicar e desfazer |
| 2. **"Mostrar só produtos sem código"** | **pronto** — filtro na tela, e ele diz *entre quantos* olhou |
| 3. **Gerar código de barras** | **motor pronto** (`etiquetas/numeracao.py`); falta a tela |
| 4. **Screencast** | não começou — roteiro em [`screencast.md`](screencast.md) |
| 5. **Os US$ 19** | depois |

Entrar com o que o mercado compra, não com o que a gente achou bonito.

### A decisão de 20/10: o escopo de escrita espera

O gerador só **grava** com `write_products`, e ligar esse escopo mexe no que é
público — política de privacidade, a frase da ficha, o `shopify.app.toml`, e
reinstalar na loja. Decidido: **ligar uma vez só, quando SKU e código de barras
estiverem os dois prontos.** Menos reinstalação, e uma revisão só na Shopify.

Até lá a prévia funciona inteira e **não pede escopo nenhum** — dá pra ver a
tabela do que *seria* gravado sem o app ter permissão de escrever nada.

### O defeito que o gerador revelou no app que já existia

Montando o caso 3 (código a partir do SKU), a medição mostrou:

```
codigos.validar("CAFÉ-01", CODE128)  ->  (True, "")
```

**O Code 128 só codifica ASCII**, e o validador liberava qualquer texto — a
linha dizia *"Code128 e QR aceitam texto"*, o que vale pro QR e não pro Code
128. Com isso, um produto de SKU acentuado:

- **no PDF** estourava `ValueError: Illegal barcode` dentro do reportlab, o que
  chega ao lojista como erro de servidor, sem explicação;
- **no ZPL** ia inteiro pra impressora, pra sair lixo ou não sair.

Num catálogo em português isso não é caso de borda: *CAFÉ*, *AÇÚCAR* e
*CAMISA-ÇÃO* são nomes de produto comuns, e SKU sai de nome de produto.

Corrigido em `codigos.validar`, que agora nomeia o caractere a tirar. A
fronteira (ASCII 32–126) foi **medida contra o reportlab**, não adivinhada.

## Em uma frase

O app está pronto, no ar e funcionando numa loja real. **A primeira mensagem foi
enviada.** Não falta código; falta um lojista.

---

## O que aconteceu em 30/08/2026

Foi um dia longo. Em ordem, e o que cada coisa custou ou revelou.

### O terreno mudou de figura

A pesquisa que originou o projeto tinha um buraco: olhou as avaliações ruins do
app oficial e **nunca perguntou quem já atendia aquela gente**. Atendia — o
*Yanet* tem 4,9 com 448 avaliações, e o *LabelFast* nasceu em 06/07/2026 com a
mesma lista de diferenciais. Ver [`quem-mais-esta-aqui.md`](quem-mais-esta-aqui.md).

Isso **não** matou o projeto: concorrente bom prova que o mercado paga, e a meta
de R$ 500–2.000/mês são 12 a 50 lojas pagantes.

### O que foi construído

| | por quê |
|---|---|
| Avery 5167 e rolo 1"×1" | pedidos por nome nas avaliações |
| Medida livre (8–300mm) | idem |
| ITF-14 | código de caixa de atacado; o único dos 3 símbolos que faltavam que muda algo |
| Dígitos sob o código viram escolha | na 5167 faltavam 0,07mm pro SKU caber |
| Grátis 100 → 200 etiquetas | é o que a categoria dá |
| Leitor de código enfileira sozinho | bipar, bipar, bipar, imprimir |
| Prévia diz por que o código sumiu | sumir calado é o defeito que o app combate |

### Os defeitos que apareceram no caminho

Todos achados **medindo**, nenhum lendo código:

1. **O app nunca conferia se o código cabia na LARGURA.** Um EAN-13 precisa de
   28,3mm; a etiqueta de 1"×1" tem 25,4mm. Medida livre teria tornado isso rotina.
2. **O QR saía de tamanhos diferentes por impressora** — 18,0mm no PDF, 16,5mm no
   ZPL. Com URL longa, ia para fora da etiqueta.
3. **A Shopify parou de aceitar o token que não expira**, e o app parou de listar
   produtos em produção. Migrado para token de 1h + renovação de 90 dias.
4. **A renovação tinha corrida:** a tela dispara 3 chamadas paralelas, e 2 de 3
   mandavam o lojista reinstalar. Toda vez que ele abrisse o app depois de 1h.
5. **UPC-A com dígito verificador errado ia pro papel** — bipa o produto errado
   no caixa. A conferência existia só para EAN-13.
6. **A fila de impressão perdia produto escolhido em busca anterior.** Contador
   dizia 2, PDF saía com 1.
7. **A instalação tentava assinar os webhooks de privacidade pela API**, que não
   aceita. Falhava em silêncio — e sem a declaração estática o app é **reprovado**.
8. **O ITF-14 sairia 21% mais largo na Zebra** que no PDF, por razão de barra
   diferente entre as bibliotecas.

### O estado técnico

**976 checagens, 71 de 71 sabotagens.** No ar em
`https://etikbarcode.pythonanywhere.com`.

---

## A decisão tomada

**O app não gera código de barras**, e o gatilho para reabrir está escrito em
[`decisao-gerar-codigo.md`](decisao-gerar-codigo.md): *um lojista de verdade
dizer que não consegue usar porque os produtos dele não têm código*.

---

## A próxima ação

### Feito
- [x] **Patch Magazine** (Reino Unido) — enviada em **30/08/2026** para
      `contact@patchmagazine.co.uk`, do `rjuan.andrade99@gmail.com`

### Próximas — contatos já achados
- [ ] **THATS-RALLY** (Alemanha) — `info@thats-rally.de`
- [ ] **Bhumi Organic Cotton** (Austrália) — `help@bhumi.com.au`
- [ ] **Maiocchi** (Austrália) — `e-boutique@maiocchi.com.au`, guardar pra
      próxima leva: mesma queixa da Bhumi

### E uma descoberta que encolheu o canal

**A Shopify não expõe a loja de quem avalia.** Sobra nome e país. De sete
tentadas, **quatro são alcançáveis** — Saratoga só tem telefone, e Frip'Dream e
The Scented Cardinal não existem em busca nenhuma, nem no Instagram.

Marca com loja física é encontrável; loja pequena só-online não é. Isso joga a
favor (loja física é quem imprime etiqueta de prateleira), mas **derruba a
premissa do plano**: 8 mensagens viraram 4, e a expectativa de resposta caiu de
1–2 para 0,4–1,2. O canal sozinho provavelmente não dá o sinal que justificaria
adiar a submissão.

### As regras combinadas

- **Duas ou três por dia**, não todas de uma vez. Contato de lojista é **não
  renovável**: só existe uma primeira mensagem por loja.
- **Guardar duas na reserva.** Se as seis primeiras derem zero, reescrever a
  mensagem e testar nessas duas — é a única forma de separar "e-mail frio não
  funciona" de "meu e-mail não funciona".
- **Expectativa honesta:** 10 a 30% de resposta. Com oito enviadas, espera-se
  **uma ou duas**. Zero de três não significa nada; zero de oito é sinal.
- **Critério de parada:** duas semanas, cinco enviadas, nenhuma resposta → o
  canal está errado e muda.

### E se alguém disser sim

É só aí que se gasta dinheiro. A lista completa está em
[`antes-de-submeter.md`](antes-de-submeter.md); o resumo:

1. ~~Declarar os 3 webhooks de privacidade~~ — **feito em 31/08/2026**, versão
   `etik-barcode-labels-5`, pela CLI (o formulário do painel não tem esse campo)
2. Gravar o screencast (exigido) — roteiro em [`screencast.md`](screencast.md)
3. Escrever as instruções de teste, incluindo como o revisor alcança o Pro
4. Pagar os **US$ 19** — uma vez por conta, para sempre
5. Renovar o PythonAnywhere e pôr lembrete — app fora do ar durante a revisão é
   reprovação certa

**A Shopify fica com 0% da receita até US$ 1.000.000.** Só 2,9% de processamento.
