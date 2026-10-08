from .base import *

# Local-only key for the docker-compose/nginx-uwsgi stack. Not for production.
SECRET_KEY = 'docker-compose-local-only-not-for-production'

# Send e-mails to the maildev container of docker-compose.yml (service "smtp").
# Without this Django tries localhost:25, which does not exist in the container,
# and every signature or account creation ends with HTTP 500.
# Read the mails at http://127.0.0.1:8080
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp'
EMAIL_PORT = 2525
