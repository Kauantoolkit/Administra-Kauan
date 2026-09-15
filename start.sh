#!/usr/bin/env bash
# Partida do servico.
#
# migrate/seed rodam AQUI, e nao no build, de proposito: no plano gratuito o
# disco e efemero e o SQLite desaparece toda vez que o servico hiberna. Rodando
# na partida, o banco e reconstruido a cada acordar e o sistema nunca sobe sem
# tabela. O preco e que dados digitados durante o teste nao sobrevivem a
# hibernacao — para persistir de verdade, use Postgres (DATABASE_URL) ou a VPS.
set -o errexit

python manage.py migrate --no-input
python manage.py seed_inicial --demo
python manage.py criar_admin

# Estado de acesso no log da partida. Sem shell no plano gratuito, esta e a
# unica forma de saber por que um login falhou. Nao imprime senha.
python manage.py diagnostico_acesso

exec gunicorn Administra.wsgi:application --bind "0.0.0.0:${PORT:-8000}"
