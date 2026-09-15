#!/usr/bin/env bash
# Build: apenas o que depende de rede e nao depende do banco.
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
