# Subir o app na Oracle Cloud

Do zero até o app no ar, com HTTPS, sempre ligado e sem custo.

A ordem importa: **DNS antes do script**, senão o certificado falha e você
precisa rodar tudo de novo.

---

## O que só você pode fazer (uma vez)

### 1. Conta na Oracle Cloud

**cloud.oracle.com** → *Start for free*.

Pede cartão para verificar identidade. **Always Free não cobra** — mas confira,
ao final do cadastro, que a conta ficou como *Always Free*. Se ela entrar como
avaliação paga, cobra depois de 30 dias.

Escolha uma região perto do Brasil: **Brazil East (São Paulo)** ou
*Brazil Southeast (Vinhedo)*. A região não muda depois.

### 2. Criar a máquina

*Compute → Instances → Create instance*:

| campo | valor |
|---|---|
| Image | **Ubuntu 24.04** (não Oracle Linux) |
| Shape | **Ampere A1** — 1 OCPU e 6 GB já sobra |
| SSH key | **Save private key** e guarde o arquivo |

> Se a Oracle disser que não há capacidade Ampere na região, use
> *VM.Standard.E2.1.Micro* (AMD). É menor e serve.

Anote o **Public IP address**.

### 3. Um nome para a máquina

O Shopify exige HTTPS com certificado válido, e certificado precisa de nome —
IP não vale. **duckdns.org** dá um subdomínio de graça, entrando com Google ou
GitHub.

Crie algo como `etik` e aponte para o IP da máquina. Fica
`etik.duckdns.org`.

> **Espere uns dez minutos** antes de seguir. Se o nome ainda não estiver
> propagado, o certificado falha. Para conferir, no seu computador:
> `nslookup etik.duckdns.org` — tem que devolver o IP da máquina.

### 4. Liberar as portas na Oracle

Este é **o passo que mais derruba montagem na Oracle**, porque quando falta ele
o site simplesmente não responde e não há erro nenhum no servidor para olhar.

*Networking → Virtual Cloud Networks →* sua VCN *→ Security Lists →* a default
*→ Add Ingress Rules*, duas vezes:

| Source CIDR | Protocol | Destination Port |
|---|---|---|
| `0.0.0.0/0` | TCP | `80` |
| `0.0.0.0/0` | TCP | `443` |

---

## Rodar o script

Entre na máquina (no PowerShell, com a chave que você baixou):

```bash
ssh -i C:\caminho\da\chave.key ubuntu@SEU-IP
```

E rode:

```bash
curl -fsSL https://raw.githubusercontent.com/rjuan98/etiquetas/main/deploy/preparar-servidor.sh -o preparar.sh && sudo bash preparar.sh etik.duckdns.org seu@email.com
```

> O repositório é privado, então esse `curl` não vai funcionar direto. Copie o
> conteúdo de `deploy/preparar-servidor.sh` para um arquivo na máquina — ou
> passe pelo `scp` — e rode `sudo bash preparar.sh etik.duckdns.org seu@email.com`.

**Ele vai parar na primeira vez, de propósito.** Como o repositório é privado, o
servidor precisa de permissão de leitura: o script gera uma chave, mostra ela na
tela, e você a cadastra em

*github.com/rjuan98/etiquetas → Settings → Deploy keys → Add deploy key*

**Só leitura.** Não marque *Allow write access* — um servidor exposto à internet
não tem por que poder escrever no seu código.

Aí rode o script de novo. Ele continua de onde parou.

---

## Depois

O script termina dizendo o que falta. Em resumo:

1. preencher os segredos em `/opt/etiquetas/.env`
2. `sudo systemctl restart etiquetas`
3. `curl https://etik.duckdns.org/saude` → tem que vir `{"ok": true, "configuracao_faltando": []}`
4. trocar os três endereços no painel do app no Shopify

Se a lista `configuracao_faltando` não vier vazia, ela diz exatamente o que falta.

---

## O dia a dia

```bash
# atualizar depois de um git push
sudo -u etiquetas git -C /opt/etiquetas pull && sudo systemctl restart etiquetas

# ver o que está acontecendo
sudo journalctl -u etiquetas -f

# o app está de pé?
systemctl status etiquetas
```

---

## Quando algo não funcionar

**O site não responde.** Quase sempre é a lista de segurança da Oracle (passo 4).
Confira de fora: `curl -v http://SEU-IP` — se pendurar sem resposta, é ela.

**O certificado falhou.** DNS ainda não propagou, ou a porta 80 está fechada.
Corrija e rode o script de novo; ele só refaz o que falta.

**O app não sobe.** `sudo journalctl -u etiquetas -n 50` mostra o motivo. O mais
comum é o `.env` incompleto — e nesse caso ele diz qual variável falta, porque o
app recusa subir mal configurado em vez de subir quebrado.

---

## Duas coisas que passam a ser suas

**O servidor é seu.** A atualização automática de segurança fica ligada, mas de
vez em quando vale entrar e rodar `sudo apt update && sudo apt upgrade`.

**O banco também.** Ele fica em `/opt/etiquetas/dados.db` e tem os modelos de
todas as lojas. Vale copiar de vez em quando:

```bash
sudo sqlite3 /opt/etiquetas/dados.db ".backup /tmp/copia.db"
```

E baixar essa cópia para o seu computador. O token de acesso das lojas está
cifrado nela — mas a cópia ainda é o catálogo de quem confiou em você.
