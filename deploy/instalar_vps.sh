#!/usr/bin/env bash
# Instalação do Administra em uma VPS Ubuntu/Debian limpa.
#
#   sudo bash deploy/instalar_vps.sh meudominio.com.br
#
# Sem domínio, passe o IP da VPS. O script instala dependências, cria o
# ambiente virtual, gera o .env, aplica migrações e sobe o serviço.

set -euo pipefail

DOMINIO="${1:-}"
if [[ -z "$DOMINIO" ]]; then
  echo "Uso: sudo bash deploy/instalar_vps.sh <dominio-ou-ip>" >&2
  exit 1
fi

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
USUARIO="${SUDO_USER:-$USER}"

echo "==> Instalando dependências do sistema"
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip nginx

echo "==> Criando ambiente virtual"
python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip -q
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt" -q

if [[ ! -f "$APP_DIR/.env" ]]; then
  echo "==> Gerando .env"
  CHAVE="$("$APP_DIR/.venv/bin/python" -c \
    'from django.core.management.utils import get_random_secret_key as g; print(g())')"
  cat > "$APP_DIR/.env" <<ENV
DJANGO_SECRET_KEY=$CHAVE
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=$DOMINIO,localhost,127.0.0.1
DJANGO_CSRF_TRUSTED_ORIGINS=https://$DOMINIO,http://$DOMINIO
DJANGO_TIME_ZONE=America/Sao_Paulo
DJANGO_SECURE_SSL_REDIRECT=false
ENV
  chmod 600 "$APP_DIR/.env"
fi

echo "==> Banco e arquivos estáticos"
"$APP_DIR/.venv/bin/python" "$APP_DIR/manage.py" migrate --noinput
"$APP_DIR/.venv/bin/python" "$APP_DIR/manage.py" collectstatic --noinput
"$APP_DIR/.venv/bin/python" "$APP_DIR/manage.py" seed_inicial

echo "==> Serviço systemd"
cat > /etc/systemd/system/administra.service <<UNIT
[Unit]
Description=Administra
After=network.target

[Service]
User=$USUARIO
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/.venv/bin/gunicorn Administra.wsgi:application --bind 127.0.0.1:8000 --workers 3
Restart=always

[Install]
WantedBy=multi-user.target
UNIT

echo "==> Nginx"
cat > /etc/nginx/sites-available/administra <<NGINX
server {
    listen 80;
    server_name $DOMINIO;
    client_max_body_size 10M;

    location /static/ { alias $APP_DIR/staticfiles/; }
    location /media/  { alias $APP_DIR/media/; }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
NGINX
ln -sf /etc/nginx/sites-available/administra /etc/nginx/sites-enabled/administra
rm -f /etc/nginx/sites-enabled/default
nginx -t

systemctl daemon-reload
systemctl enable --now administra
systemctl restart nginx

echo
echo "Pronto. Acesse: http://$DOMINIO"
echo "Crie o primeiro usuário com:"
echo "  $APP_DIR/.venv/bin/python $APP_DIR/manage.py createsuperuser"
echo
echo "Para HTTPS (recomendado antes de vender):"
echo "  apt install certbot python3-certbot-nginx && certbot --nginx -d $DOMINIO"
echo "  depois troque DJANGO_SECURE_SSL_REDIRECT=true no .env e reinicie."
