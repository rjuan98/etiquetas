# Subir no PythonAnywhere

O caminho de graça, com HTTPS pronto e sem domínio para comprar.

É mais simples que um servidor de verdade — não tem nginx, nem certificado, nem
sistema operacional para manter. Em troca vêm três limites que você precisa
conhecer **antes**, porque um deles pode derrubar o app.

---

## Os três limites, sem enfeite

**O app web expira em 1 mês.** Você precisa entrar e clicar para renovar. Se
esquecer, o app cai — e cair aqui não é só tela de erro: o Shopify desassina os
webhooks depois de 48h de falha, e `shop/redact` é obrigatório para continuar na
loja de apps.

> **Ponha um lembrete mensal no celular agora.** É o único jeito.

**100 segundos de CPU por dia.** Gerar PDF é CPU: um lote de 500 etiquetas come
uns 2 segundos. Dá para muita coisa, mas um lojista imprimindo a prateleira
inteira várias vezes consegue esgotar o dia — e aí o app fica lento para todos
até virar a meia-noite.

**A saída passa por um proxy, com lista de sites permitidos.** `.myshopify.com`
está na lista, então funciona. O app já sabe lidar com isso (`PROXY_SAIDA` no
`.env`), mas é uma dependência da lista de outra pessoa.

Nada disso impede começar. Tudo isso some com o plano Hacker, US$ 5/mês — e a
hora de fazer essa conta é quando entrar o primeiro dinheiro, não antes.

---

## 1. A conta

Crie uma **segunda conta grátis** em pythonanywhere.com, separada da que roda o
Hércules. Os termos deles não proíbem, e o plano grátis dá um app web só — por
isso os dois não cabem juntos.

O nome de usuário vira o endereço do app. Escolha pensando nisso:
`etikbarcode` vira `https://etikbarcode.pythonanywhere.com`.

> Anote o endereço. Ele vai no painel do Shopify e no `.env`.

---

## 2. Dar acesso ao código

O repositório é privado, e a conta grátis não faz SSH para fora. O jeito é um
**token de leitura** pelo HTTPS.

No GitHub: *Settings → Developer settings → Personal access tokens →
Fine-grained tokens → Generate new token*

| campo | valor |
|---|---|
| Repository access | **Only select repositories** → `etiquetas` |
| Permissions → Contents | **Read-only** |
| Expiration | 90 dias, e renove junto com o lembrete mensal |

Só leitura, e só neste repositório. O token vai ficar guardado no servidor — um
que só lê um repositório é um estrago pequeno se vazar.

---

## 3. Instalar

Abra um **Bash console** no PythonAnywhere e cole isto, trocando `SEU_TOKEN`:

```bash
git clone https://SEU_TOKEN@github.com/rjuan98/etiquetas.git ~/etiquetas
cd ~/etiquetas
python3.11 -m venv .venv
.venv/bin/pip install -r requisitos.txt
python3 -c "import secrets; print('CHAVE_SEGREDO=' + secrets.token_urlsafe(32))"
```

A última linha imprime a chave que cifra os tokens das lojas. **Copie**, você vai
usar já.

> Se `python3.11` não existir, veja quais versões há com `ls /usr/bin/python3.*`
> e use a mais nova. O app precisa de 3.9 ou mais.

---

## 4. A configuração

Ainda no console:

```bash
nano ~/etiquetas/.env
```

Cole, preenchendo o que falta:

```
CHAVE_SEGREDO=<a que você acabou de gerar>

SHOPIFY_CHAVE_API=<Client ID, do painel do app>
SHOPIFY_SEGREDO=<Client secret, do painel do app>
SHOPIFY_SEGREDO_ANTIGO=

APP_URL=https://SEUUSUARIO.pythonanywhere.com
BANCO_CAMINHO=/home/SEUUSUARIO/etiquetas/dados.db

MODO_DEV=0
COBRANCA_TESTE=0

CONTATO_EMAIL=<um e-mail que você lê de verdade>
CONTATO_NOME=<seu nome ou o do MEI>
HOSPEDAGEM=PythonAnywhere

# Sem isto o app não fala com o Shopify no plano grátis.
PROXY_SAIDA=http://proxy.server:3128
```

Salvar é `Ctrl+O`, `Enter`, `Ctrl+X`.

> **Cole só o valor, mantendo o nome antes do `=`.** Colar por cima da linha
> inteira apaga o nome da variável e o app sobe achando que não tem segredo —
> foi exatamente o que aconteceu na primeira vez que fizemos isso.

---

## 5. Criar o app web

Na aba **Web** → *Add a new web app*:

1. domínio: o padrão (`SEUUSUARIO.pythonanywhere.com`)
2. framework: **Manual configuration** (não escolha Flask)
3. versão do Python: a mesma que você usou no venv

Depois, na mesma página:

| campo | valor |
|---|---|
| Source code | `/home/SEUUSUARIO/etiquetas` |
| Working directory | `/home/SEUUSUARIO/etiquetas` |
| Virtualenv | `/home/SEUUSUARIO/etiquetas/.venv` |

E clique em **WSGI configuration file**. Apague tudo o que estiver lá e ponha:

```python
import os
import sys

RAIZ = "/home/SEUUSUARIO/etiquetas"
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

# O servidor.py lê o .env e resolve os caminhos a partir do próprio arquivo,
# então basta importar. O `application` é o nome que o PythonAnywhere procura.
from servidor import app as application  # noqa: E402
```

Salve e clique no botão verde **Reload**.

---

## 6. Conferir

No seu computador:

```bash
curl https://SEUUSUARIO.pythonanywhere.com/saude
```

Tem que responder:

```json
{"ok": true, "configuracao_faltando": []}
```

Se a lista não vier vazia, ela diz exatamente qual variável falta. Se der erro
500, o motivo está na aba **Web → Error log**, no fim do arquivo.

---

## 7. Apontar o Shopify para cá

No painel do app, troque os três endereços:

| campo | valor |
|---|---|
| App URL | `https://SEUUSUARIO.pythonanywhere.com` |
| Allowed redirection URL | `https://SEUUSUARIO.pythonanywhere.com/instalar/volta` |
| Os três webhooks | `https://SEUUSUARIO.pythonanywhere.com/webhooks` |

Depois **reinstale o app na loja Etik** — o endereço mudou, e a instalação
antiga aponta para o túnel que não existe mais.

---

## O dia a dia

```bash
# atualizar depois de um git push
cd ~/etiquetas && git pull
# e clicar em Reload na aba Web

# o banco, de vez em quando
sqlite3 ~/etiquetas/dados.db ".backup ~/copia.db"
```

Baixe a cópia pelo painel de **Files**. O token das lojas está cifrado nela, mas
ela ainda é o trabalho de quem confiou em você.

---

## Quando trocar de hospedagem

Quando entrar dinheiro, ou quando um dos três limites incomodar. O plano Hacker
(US$ 5/mês) tira a expiração, tira a lista de sites e dá bem mais CPU — e nesse
caso você só apaga a linha `PROXY_SAIDA` do `.env` e recarrega.

Se um dia for para um servidor de verdade, o `deploy/preparar-servidor.sh` faz
tudo sozinho. Ele foi escrito para a Oracle, mas serve em qualquer Ubuntu.
