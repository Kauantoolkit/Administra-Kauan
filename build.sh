#!/usr/bin/env bash
# Executado pela plataforma de deploy a cada publicação.
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate --no-input

# Categorias padrão e configuração da loja. --demo popula produtos de exemplo
# cobrindo todos os modos de venda; remova a flag para subir a loja vazia.
python manage.py seed_inicial --demo

# Cria o administrador a partir de ADMIN_EMAIL/ADMIN_SENHA, quando definidos.
python manage.py criar_admin
