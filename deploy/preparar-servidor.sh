#!/usr/bin/env bash
#
# Monta o servidor inteiro, do zero, numa máquina Ubuntu da Oracle Cloud.
#
#   sudo bash preparar-servidor.sh SEU-NOME.duckdns.org seu@email.com
#
# Pode rodar de novo quantas vezes quiser: cada passo confere antes de agir.
# Isso é de propósito — a primeira tentativa quase nunca passa inteira, e um
# script que só funciona uma vez obriga a começar do zero quando falha no meio.
#
# ------------------------------------------------------------------ o que ele faz
#   1. abre as portas 80 e 443 na máquina (a Oracle bloqueia por padrão)
#   2. instala Python, nginx e o certbot
#   3. cria um usuário sem privilégios pro app rodar
#   4. baixa o código do GitHub (repositório privado, por chave de leitura)
#   5. monta o ambiente virtual e instala as dependências
#   6. cria o serviço, pra subir sozinho no boot e reiniciar se cair
#   7. põe o nginx na frente e pede o certificado HTTPS
#   8. liga atualização automática de segurança
#
# ------------------------------------------------------- o que ele NÃO faz
#   Não preenche o `.env`. Os segredos são seus e não entram em script nenhum —
#   o próprio script te diz o que preencher e para no ponto certo.

set -euo pipefail

DOMINIO="${1:-}"
EMAIL="${2:-}"
REPO="git@github.com:rjuan98/etiquetas.git"
USUARIO="etiquetas"
PASTA="/opt/etiquetas"
PORTA_INTERNA=8000

vermelho() { printf "\033[31m%s\033[0m\n" "$*"; }
verde()    { printf "\033[32m%s\033[0m\n" "$*"; }
titulo()   { printf "\n\033[1m== %s\033[0m\n" "$*"; }

if [[ -z "$DOMINIO" || -z "$EMAIL" ]]; then
  vermelho "Faltou o domínio ou o e-mail."
  echo "  sudo bash preparar-servidor.sh SEU-NOME.duckdns.org seu@email.com"
  echo
  echo "O e-mail é pro Let's Encrypt avisar quando o certificado for expirar."
  exit 1
fi
if [[ $EUID -ne 0 ]]; then
  vermelho "Rode com sudo."
  exit 1
fi

titulo "1. Abrindo as portas 80 e 443"
# A imagem Ubuntu da Oracle vem com iptables barrando tudo menos SSH, E a rede
# virtual tem uma lista de segurança separada. As duas precisam liberar — e é
# aqui que a maioria das montagens na Oracle empaca, porque o site simplesmente
# não responde e nada no servidor acusa erro.
if ! iptables -C INPUT -p tcp --dport 80 -j ACCEPT 2>/dev/null; then
  iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
fi
if ! iptables -C INPUT -p tcp --dport 443 -j ACCEPT 2>/dev/null; then
  iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
fi
DEBIAN_FRONTEND=noninteractive apt-get install -y iptables-persistent >/dev/null 2>&1 || true
netfilter-persistent save >/dev/null 2>&1 || true
verde "   portas liberadas na máquina"
echo "   ATENÇÃO: falta liberar também na Oracle, no painel dela."
echo "   Networking → Virtual Cloud Networks → sua VCN → Security Lists →"
echo "   Add Ingress Rules: 0.0.0.0/0, TCP, portas 80 e 443."

titulo "2. Instalando o que o servidor precisa"
DEBIAN_FRONTEND=noninteractive apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
  python3 python3-venv python3-pip git nginx certbot python3-certbot-nginx \
  unattended-upgrades
verde "   instalado"

titulo "3. Criando o usuário do app"
if ! id "$USUARIO" >/dev/null 2>&1; then
  useradd --system --create-home --shell /usr/sbin/nologin "$USUARIO"
fi
# O app roda sem privilégio nenhum. Se um dia ele for invadido, o estrago para
# no que este usuário alcança — e ele não alcança quase nada.
verde "   usuário $USUARIO pronto"

titulo "4. Baixando o código"
if [[ ! -f /home/$USUARIO/.ssh/id_ed25519 ]]; then
  sudo -u "$USUARIO" mkdir -p /home/$USUARIO/.ssh
  sudo -u "$USUARIO" ssh-keygen -t ed25519 -N "" -f /home/$USUARIO/.ssh/id_ed25519 -q
  sudo -u "$USUARIO" ssh-keyscan -H github.com >> /home/$USUARIO/.ssh/known_hosts 2>/dev/null
  echo
  vermelho "   PARE AQUI. O repositório é privado e o servidor precisa de acesso."
  echo
  echo "   Copie a chave abaixo e cadastre no GitHub como DEPLOY KEY:"
  echo "   github.com/rjuan98/etiquetas → Settings → Deploy keys → Add deploy key"
  echo "   Marque SÓ leitura. Não marque 'Allow write access'."
  echo
  cat /home/$USUARIO/.ssh/id_ed25519.pub
  echo
  echo "   Feito isso, rode este script de novo."
  exit 0
fi

if [[ -d "$PASTA/.git" ]]; then
  sudo -u "$USUARIO" git -C "$PASTA" pull --ff-only
else
  mkdir -p "$PASTA"
  chown "$USUARIO:$USUARIO" "$PASTA"
  sudo -u "$USUARIO" git clone "$REPO" "$PASTA"
fi
verde "   código em $PASTA"

titulo "5. Montando o ambiente e as dependências"
if [[ ! -d "$PASTA/.venv" ]]; then
  sudo -u "$USUARIO" python3 -m venv "$PASTA/.venv"
fi
sudo -u "$USUARIO" "$PASTA/.venv/bin/pip" install -q --upgrade pip
sudo -u "$USUARIO" "$PASTA/.venv/bin/pip" install -q -r "$PASTA/requisitos.txt"
verde "   dependências instaladas"

titulo "6. Configuração"
if [[ ! -f "$PASTA/.env" ]]; then
  CHAVE=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
  cat > "$PASTA/.env" <<FIM
# Gerada pelo servidor. NUNCA troque depois de instalar lojas: os tokens de
# acesso guardados param de abrir e todas as lojas precisam reinstalar o app.
CHAVE_SEGREDO=$CHAVE

# Do painel do app no Shopify, em Client credentials.
SHOPIFY_CHAVE_API=
SHOPIFY_SEGREDO=
SHOPIFY_SEGREDO_ANTIGO=

APP_URL=https://$DOMINIO
BANCO_CAMINHO=$PASTA/dados.db

# 0 em produção, sempre. Com 1, o traceback do Flask fica exposto e a rota
# /dev/ existe.
MODO_DEV=0

# Aparecem na política de privacidade, que é pública.
CONTATO_EMAIL=
CONTATO_NOME=
HOSPEDAGEM=Oracle Cloud (Brasil)
FIM
  chown "$USUARIO:$USUARIO" "$PASTA/.env"
  chmod 600 "$PASTA/.env"
  verde "   .env criado, com a CHAVE_SEGREDO já sorteada"
else
  verde "   .env já existe, mantido como está"
fi

titulo "7. Criando o serviço"
cat > /etc/systemd/system/etiquetas.service <<FIM
[Unit]
Description=Etik Barcode Labels
After=network.target

[Service]
User=$USUARIO
WorkingDirectory=$PASTA
# 3 processos: um lote grande de PDF ocupa um por vários segundos, e sem os
# outros o app inteiro ficaria parado esperando.
ExecStart=$PASTA/.venv/bin/gunicorn --workers 3 --timeout 120 \\
          --bind 127.0.0.1:$PORTA_INTERNA --access-logfile - servidor:app
Restart=always
RestartSec=5

# O processo só enxerga o que precisa. Se for invadido, o estrago para aqui.
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$PASTA

[Install]
WantedBy=multi-user.target
FIM
systemctl daemon-reload
systemctl enable --now etiquetas >/dev/null 2>&1 || systemctl restart etiquetas
verde "   serviço criado e ligado (sobe sozinho no boot)"

titulo "8. Pondo o nginx na frente"
cat > /etc/nginx/sites-available/etiquetas <<FIM
server {
    listen 80;
    server_name $DOMINIO;

    location / {
        proxy_pass http://127.0.0.1:$PORTA_INTERNA;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        # Lote de 5000 etiquetas leva uns 20 segundos. O padrão de 60s do nginx
        # cortaria a resposta no meio e o lojista veria erro numa impressão que
        # o servidor estava gerando direitinho.
        proxy_read_timeout 180s;
    }

    # O corpo do webhook do Shopify é pequeno, mas o do modelo não é.
    client_max_body_size 4m;
}
FIM
ln -sf /etc/nginx/sites-available/etiquetas /etc/nginx/sites-enabled/etiquetas
rm -f /etc/nginx/sites-enabled/default
nginx -t >/dev/null && systemctl reload nginx
verde "   nginx configurado"

titulo "9. Certificado HTTPS"
if [[ -d "/etc/letsencrypt/live/$DOMINIO" ]]; then
  verde "   certificado já existe"
else
  # O Shopify exige https com certificado válido — IP não serve, e autoassinado
  # também não. O certbot renova sozinho por um timer do systemd.
  certbot --nginx -d "$DOMINIO" --non-interactive --agree-tos -m "$EMAIL" --redirect \
    || vermelho "   O certificado falhou. Quase sempre é o DNS ainda não ter
   propagado, ou a porta 80 fechada na lista de segurança da Oracle.
   Confira e rode o script de novo."
fi

titulo "10. Atualização automática de segurança"
dpkg-reconfigure -f noninteractive unattended-upgrades >/dev/null 2>&1 || true
verde "   ligada"

echo
titulo "Pronto. Agora falta você:"
cat <<FIM

  1. Liberar as portas 80 e 443 no painel da Oracle, se ainda não liberou:
     Networking → Virtual Cloud Networks → sua VCN → Security Lists →
     Add Ingress Rules: 0.0.0.0/0, TCP, portas 80 e 443

  2. Preencher os segredos:
     sudo nano $PASTA/.env
     (SHOPIFY_CHAVE_API, SHOPIFY_SEGREDO, CONTATO_EMAIL, CONTATO_NOME)

  3. Reiniciar e conferir:
     sudo systemctl restart etiquetas
     curl https://$DOMINIO/saude

     Tem que responder {"ok": true, "configuracao_faltando": []}.
     Se a lista não vier vazia, ela diz exatamente o que falta no .env.

  4. No painel do app no Shopify, trocar os endereços pra:
     App URL ............ https://$DOMINIO
     Redirection URL .... https://$DOMINIO/instalar/volta
     Webhooks ........... https://$DOMINIO/webhooks

  Pra atualizar o app depois de um git push:
     sudo -u $USUARIO git -C $PASTA pull && sudo systemctl restart etiquetas

  Pra ver o que está acontecendo:
     sudo journalctl -u etiquetas -f

FIM
