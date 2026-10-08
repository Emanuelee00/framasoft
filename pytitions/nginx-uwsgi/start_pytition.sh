#!/usr/bin/env sh
set -e

# we collect the static
python3 pytition/manage.py collectstatic --noinput
# nginx runs as the nginx user: the collected files must be readable by everyone
chmod a+rx "$(dirname "$STATIC_ROOT")"
chmod -R a+rX "$STATIC_ROOT"

# the .mo files are not in git: compile the translations
(cd pytition && python3 manage.py compilemessages -v 0)

# wait for postgres to start
while ! nc -z db 5432; do echo "waiting for postgres to start..." && sleep 1; done;

# and initialize the db, ignore the errors
python3 pytition/manage.py migrate

# we call the base image entry point (that will start nginx/uwsgi)
echo "starting pytition"
exec /entrypoint.sh "/usr/bin/supervisord"
