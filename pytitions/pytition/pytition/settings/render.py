import os
from urllib.parse import unquote, urlparse

from .base import *

# Settings for the Render deployment (see render.yaml at the root of the repository).
# Everything that changes between deployments is read from environment variables.

# Render generates it (render.yaml); the missing variable makes the start fail on purpose.
SECRET_KEY = os.environ['SECRET_KEY']
DEBUG = False

# Render sets RENDER_EXTERNAL_HOSTNAME (xxx.onrender.com); ALLOWED_HOSTS adds custom domains,
# comma separated.
ALLOWED_HOSTS = [host for host in os.environ.get('ALLOWED_HOSTS', '').split(',') if host]
if os.environ.get('RENDER_EXTERNAL_HOSTNAME'):
    ALLOWED_HOSTS.append(os.environ['RENDER_EXTERNAL_HOSTNAME'])
CSRF_TRUSTED_ORIGINS = ['https://' + host for host in ALLOWED_HOSTS]

# TLS ends at Render's proxy: without this Django sees plain http and rejects the CSRF check.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Render gives the database as one URL: postgresql://user:password@host:port/name
_db = urlparse(os.environ.get('DATABASE_URL', ''))
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': _db.path.lstrip('/'),
        'USER': unquote(_db.username or ''),
        'PASSWORD': unquote(_db.password or ''),
        'HOST': _db.hostname or '',
        'PORT': _db.port or '',
        'CONN_MAX_AGE': DATABASE_CONN_MAX_AGE,
        'CONN_HEALTH_CHECKS': True,
    }
}

# Render's proxy is the single proxy in front of nginx and appends the visitor's address to
# X-Forwarded-For, so the per-IP signature limit looks at the last element. Check it with a
# real signature: if every visitor shares one address, raise this value (never above the real
# number of proxies, or clients could choose their own address).
PYTITION_TRUSTED_PROXY_COUNT = int(os.environ.get('PYTITION_TRUSTED_PROXY_COUNT', '1'))

# Render's free web services block outgoing SMTP on the usual ports, so by default the e-mails
# (signature confirmations...) are printed in the service logs. Set EMAIL_HOST (and the
# variables below) to send them for real.
if os.environ.get('EMAIL_HOST'):
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.environ['EMAIL_HOST']
    EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
    EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
    EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', '1') == '1'
    DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER)
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
