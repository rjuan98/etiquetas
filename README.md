# Etiquetas

Motor de etiqueta de código de barras. Um template em milímetros vira ZPL (Zebra),
XML (DYMO) ou PDF (folha adesiva) — a mesma etiqueta, em qualquer impressora.

Construído pra virar um app da loja do Shopify, mas o motor **não sabe o que é
Shopify**. Ele recebe um template e um dicionário de dados, e devolve bytes.

---

## Por que existe

O app oficial do Shopify pra isso, o *Retail Barcode Labels*, é **o app pior
avaliado da loja inteira**: nota 2,3 com 565 avaliações, 44% delas de uma
estrela, contra uma média de 4,70 no ecossistema.

E em julho de 2026 uma atualização deles **piorou**: tirou o SKU das etiquetas
Avery, mudou a fonte e a largura do código de barras sozinha. Nas palavras de um
lojista: *"todas as minhas etiquetas não combinam mais"*.

As reclamações que se repetem, e o que este motor faz sobre cada uma:

| a reclamação | o que aqui resolve |
|---|---|
| etiqueta sai torta | calibração em milímetro, nos dois sentidos |
| a fonte mudou sozinha | template versionado + teste de arquivo-espelho |
| não dá pra tirar o campo de preço | cada elemento é escolha do lojista |
| o € fica do lado errado | símbolo, posição e separadores configuráveis |
| "digitar 1 pra cada código", com 2.000 | quantidade é parâmetro, não digitação |
| sumiu o SKU da etiqueta | texto fixo e prefixo em qualquer elemento |
| etiqueta que às vezes não bipa | zona muda como regra, não como sorte |

---

## Rodar

```bash
pip install -r requisitos.txt
python testes.py         # a bateria inteira
python exemplo.py        # gera ZPL pra colar no labelary.com/viewer.html
python exemplo.py cal    # o mesmo, com 1mm de desvio à direita e 0,5mm acima
```

Nada disso precisa de internet, conta, chave ou impressora.

---

## Como está montado

```
etiquetas/         O MOTOR — não sabe o que é Shopify
  unidades.py      mm ↔ dots ↔ pontos       ← o ÚNICO conversor
  codigos.py       simbologia, verificador, zona muda
  campos.py        "produto.titulo" → valor  ← o ÚNICO resolvedor
  texto.py         quebra, corte, encolhimento
  modelo.py        Template, Mídia, Calibração, Texto, Preço, CódigoBarras
  esquema.py       JSON, versão e validação
  formatos.py      catálogo de papel pronto (Avery, DYMO, Zebra, Pimaco)
  valores.py       o valor final de um elemento ← a ÚNICA regra
  receitas.py      escolhas do lojista → Template montado
  motores/
    zpl.py         Zebra e compatíveis
    pdf.py         folha adesiva (Avery) e rolo sem térmica
    svg.py         a prévia na tela, pelas mesmas regras

loja/              O SHOPIFY — só regra, sem rede (exceto rede.py)
  dominio.py       valida o domínio da loja   ← a peça de segurança nº 1
  assinatura.py    HMAC de webhook e de OAuth, JWT de token de sessão
  oauth.py         instalação, com `state` contra instalação forjada
  catalogo.py      GraphQL + tradução pro formato do motor
  cobranca.py      planos, pelo Shopify App Pricing
  webhooks.py      inclui os 3 obrigatórios de privacidade
  rede.py          o ÚNICO arquivo que fala com a internet

dados/             O BANCO — toda consulta filtra por loja_id
  banco.py         conexão, esquema, cifra do token de acesso
  lojas.py         instalar, reinstalar, desinstalar, apagar
  modelos.py       os modelos: o template que imprime + a receita que reabre
  impressoes.py    a conta do mês (só a conta, nada do conteúdo)

web/               O FLASK
  config.py        variáveis de ambiente, conferidas no boot
  sessao.py        @exige_loja — o portão de toda rota de dados
  rotas_instalacao.py   OAuth, com o escape do iframe
  rotas_webhooks.py     recebe, confere HMAC, responde 200 rápido
  rotas_api.py          catálogo, receita, prévia, impressão, assinatura
  rotas_cobranca.py     a volta do lojista depois de aprovar a cobrança
  rotas_tela.py         a tela: produtos à esquerda, etiqueta à direita
  dev.py                a tela rodando sem Shopify nenhum

sabotagem.py       quebra cada defesa e confere que um teste grita

espelho.py         arquivo-espelho: congela a saída byte a byte
espelhos/          as saídas congeladas
exemplos/          templates prontos
testes.py
```

### A unidade é o milímetro

Nunca dot, nunca ponto. A mesma etiqueta sai numa Zebra de 203 dpi, numa DYMO de
300 e num PDF de 72 — e milímetro é a única verdade física entre os três. Cada
motor converte na saída.

Começar em dots porque "facilita o ZPL" obriga a reescrever tudo quando entra o
segundo motor.

### Uma regra, um lugar

`unidades.py` e `campos.py` existem sozinhos de propósito. Se cada motor
converter medida ou ler campo por conta própria, os três divergem — e aí a
etiqueta muda conforme a impressora, o que é exatamente o defeito que a gente
está corrigindo.

### Calibração mora no modelo, não no motor

A primeira tentativa foi usar `^LH` do ZPL. O linter avisou: **`^LH` não aceita
valor negativo**, só desloca pra direita e pra baixo. Desvio de impressora vai
pros dois lados, então `^LH` não serve.

Aplicando no modelo, os três motores calibram igual, com o mesmo número, testado
uma vez.

### Zona muda é regra, não sorte

Todo código de barras exige papel em branco antes e depois das barras. Sem isso o
leitor não bipa — **às vezes**, que é o pior caso: funciona nos dez primeiros
testes do lojista e falha na fila do caixa.

O motor soma a margem por baixo. A pessoa posiciona onde quer e a norma é
respeitada de qualquer jeito.

---

### Uma loja nunca enxerga a outra

Toda consulta a dado de loja leva `loja_id` no `WHERE`, inclusive as que buscam
por `id` — e as funções não têm assinatura que permita chamar sem ele.

Parece redundante, já que o `id` é único no banco inteiro. Não é: sem isso, o
lojista abre `/modelos/57`, troca pra 58 e vê o modelo de outro. É a falha mais
comum de app multi-inquilino, tem nome (IDOR), e a origem é sempre a mesma —
buscar por `id` sozinho porque "o id é único".

No `UPDATE` importa ainda mais que no `SELECT`: ler o alheio é ruim, sobrescrever
o alheio não tem volta.

### O token de acesso é cifrado no banco

O token que o Shopify devolve **não expira** e dá acesso ao catálogo inteiro da
loja. Backup mal guardado, disco de servidor descartado, cópia num pendrive — em
qualquer um desses o arquivo do banco vaza inteiro.

Cifrar com uma chave que mora no ambiente separa as duas coisas. Não protege de
quem invade o servidor rodando, mas protege do caso comum, que é backup vazando.
Sem `CHAVE_SEGREDO`, o app **recusa subir**.

---

## Testes

`python testes.py` — **697 checagens**, sem rede, sem conta e sem impressora.

Duas regras herdadas do projeto anterior, e as duas custaram caro:

**O teste explica POR QUE, não só o quê.** Teste que garante o bug é pior que
teste nenhum, porque impede o conserto. Quando o motivo escrito no comentário
deixar de valer, o teste muda junto.

**Medir com cenário, não ler fórmula.** Aqui o cenário é uma etiqueta renderizada
que dá pra colar no Labelary e olhar.

### E os testes são testados

`python sabotagem.py` — quebra 25 defesas de propósito, uma por vez, e confere
que algum teste grita. Teste que passa não prova nada; prova que passou. O que
prova é o teste **falhar** quando a defesa sai.

Isso já pegou dois testes fracos meus. O do ataque `alg:none` passava porque a
conferência de assinatura salvava, não porque a checagem de algoritmo existia. E
o da linha de base do preço sabotava uma linha que não fazia trabalho nenhum.

Quando aparece "ESCAPOU", não é o código que está errado — é o teste.

---

## Rodar o app inteiro, sem Shopify nenhum

```bash
cp .env.exemplo .env      # com MODO_DEV=1
python servidor.py
```

Abre em **http://localhost:5000/dev/** com uma loja de mentira e um catálogo de
mentira — e todo o resto do caminho é o de verdade: a mesma conferência de token,
as mesmas rotas, o mesmo motor, o mesmo banco.

Sem isso, a tela só poderia ser vista depois de criar conta de Partner, criar
loja de desenvolvimento, publicar num endereço https e instalar. Ou seja: eu
escreveria a tela inteira sem nunca ter visto ela funcionar.

O `/dev/` só existe com `MODO_DEV=1`; em produção a rota não é registrada.

---

## A prévia não pode mentir

A prévia é renderizada **no servidor**, pelo motor SVG, chamando as mesmas
funções que geram o ZPL e o PDF. Desenhá-la em JavaScript seria mais rápido e
mentiria: a quebra de linha do JavaScript discordaria da do Python, e a tela
mostraria uma etiqueta que a impressora não vai imprimir.

Tem teste comparando, linha por linha, o texto do SVG com o texto do ZPL.

Pela mesma razão, o layout é montado no servidor (`receitas.py`): a tela manda
**escolhas** — quais campos, que papel, como mostrar o preço — e recebe a
etiqueta pronta. O navegador não sabe o que é milímetro.

---

## Estado

Prontos e testados: motores **ZPL**, **PDF** e **SVG** (EAN-13, UPC-A, Code128,
QR), 11 formatos de papel, o **lado Shopify** inteiro (OAuth, token de sessão,
webhooks, catálogo, cobrança), o **banco** com isolamento entre lojas, as
**rotas Flask** e a **tela** — escolher produtos, montar a etiqueta, ver a
prévia, baixar PDF ou ZPL, e a régua de calibração.

Salvar guarda **duas coisas**: o template montado, que é o que imprime, e a
receita — as escolhas que o geraram. Sem a receita dava pra imprimir e não dava
pra editar: o lojista reabriria o modelo dele e veria todos os botões no padrão,
sem relação nenhuma com a etiqueta na tela.

Falta: o motor da DYMO (precisa do aparelho pra valer a pena) e subir num
servidor de verdade.

O motor continua sem saber o que é Shopify. Se um dia a plataforma mudar de
ideia, ele vem junto inteiro.
