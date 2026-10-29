#!/usr/bin/env sh
set -e

# Render's free plan has no shell: create the admin from the DJANGO_SUPERUSER_* variables
# (username, e-mail, password). If it already exists the command fails, and that is fine.
python3 pytition/manage.py migrate --noinput
python3 pytition/manage.py gen_reasons
if [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    python3 pytition/manage.py createsuperuser --noinput || true
fi

# we call the base image entry point (that will start nginx/uwsgi)
echo "starting pytition"
exec /entrypoint.sh "/usr/bin/supervisord"
