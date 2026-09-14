"""
Django settings for Administra project.

Configuração dirigida por variáveis de ambiente (arquivo .env), para que o
mesmo código rode em desenvolvimento e em produção sem edição manual.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _env(nome, padrao=None):
    valor = os.environ.get(nome)
    return valor if valor not in (None, '') else padrao


def _env_bool(nome, padrao=False):
    valor = _env(nome)
    if valor is None:
        return padrao
    return valor.strip().lower() in ('1', 'true', 'yes', 'on', 'sim')


def _env_list(nome, padrao=''):
    valor = _env(nome, padrao) or ''
    return [item.strip() for item in valor.split(',') if item.strip()]


# Carrega um .env simples (KEY=VALOR) se existir, sem dependência externa.
_ENV_FILE = BASE_DIR / '.env'
if _ENV_FILE.exists():
    for linha in _ENV_FILE.read_text(encoding='utf-8').splitlines():
        linha = linha.strip()
        if not linha or linha.startswith('#') or '=' not in linha:
            continue
        chave, _, valor = linha.partition('=')
        os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))

DEBUG = _env_bool('DJANGO_DEBUG', False)

SECRET_KEY = _env('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'django-insecure-somente-para-desenvolvimento-local'
    else:
        raise RuntimeError(
            'DJANGO_SECRET_KEY nao definida. Defina a variavel de ambiente '
            'antes de subir o sistema em producao.'
        )

ALLOWED_HOSTS = _env_list('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,[::1]')
CSRF_TRUSTED_ORIGINS = _env_list('DJANGO_CSRF_TRUSTED_ORIGINS')


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'contas.apps.ContasConfig',
    'clientes',
    'funcionarios',
    'vendas.apps.VendasConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'Administra.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'contas.context_processors.identidade_loja',
            ],
        },
    },
]

WSGI_APPLICATION = 'Administra.wsgi.application'


# Banco de dados: SQLite por padrao, PostgreSQL quando DATABASE_URL for definida.
_DATABASE_URL = _env('DATABASE_URL')
if _DATABASE_URL:
    from urllib.parse import urlparse, unquote

    _url = urlparse(_DATABASE_URL)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': _url.path.lstrip('/'),
            'USER': unquote(_url.username or ''),
            'PASSWORD': unquote(_url.password or ''),
            'HOST': _url.hostname or '',
            'PORT': str(_url.port or ''),
            'CONN_MAX_AGE': 60,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


LANGUAGE_CODE = 'pt-br'
TIME_ZONE = _env('DJANGO_TIME_ZONE', 'America/Sao_Paulo')
USE_I18N = True
USE_TZ = True


STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'contas.CustomUser'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

# Tamanho maximo de upload em memoria (5 MB) — evita estourar RAM com imagens.
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024


# Endurecimento aplicado apenas fora do modo de desenvolvimento.
if not DEBUG:
    SECURE_SSL_REDIRECT = _env_bool('DJANGO_SECURE_SSL_REDIRECT', True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = 'same-origin'
    X_FRAME_OPTIONS = 'DENY'
    # Atras de proxy reverso (nginx/caddy), confia no cabecalho de protocolo.
    if _env_bool('DJANGO_BEHIND_PROXY', True):
        SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'root': {
        'handlers': ['console'],
        'level': _env('DJANGO_LOG_LEVEL', 'INFO'),
    },
}
