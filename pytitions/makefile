run: install db
	cd pytition && DJANGO_SETTINGS_MODULE=pytition.settings.local uv run --no-sync python manage.py runserver 127.0.0.1:8000

# Runs only the first time (the stamp file marks it as done)
install: .make-install-stamp

.make-install-stamp: pytition/pytition/settings/local.py | db
	bash migrate.sh
	cd pytition && DJANGO_SETTINGS_MODULE=pytition.settings.local uv run --no-sync python manage.py migrate
	touch .make-install-stamp

# Created only if missing, with a new random secret key
pytition/pytition/settings/local.py:
	key=$$(python3 -c "import secrets; print(secrets.token_urlsafe(50))"); \
	printf '%s\n' \
		"from pytition.settings.base import *" \
		"" \
		"SECRET_KEY = '$$key'" \
		"DEBUG = True" \
		"ALLOWED_HOSTS = ['127.0.0.1', 'localhost']" \
		"DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql', 'NAME': 'postgres', 'USER': 'postgres', 'PASSWORD': 'postgres', 'HOST': 'localhost', 'PORT': 5432}}" \
		"EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'" \
		> $@

# Starts the PostgreSQL container (created on first use) and waits until it accepts connections
db:
	podman start pytition-db >/dev/null 2>&1 || podman run -d --name pytition-db -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 docker.io/library/postgres:16 >/dev/null
	@until podman exec pytition-db pg_isready -U postgres >/dev/null 2>&1; do sleep 1; done

migrate:
	cd pytition && DJANGO_SETTINGS_MODULE=pytition.settings.local uv run --no-sync python manage.py migrate

# Stops the standalone podman DB used by `run`, so its port 5432 is free
# for the docker-compose stack's own `db` service used by `run-prod`.
stop-db:
	podman stop pytition-db >/dev/null 2>&1 || true

# Runs the app behind nginx + uWSGI (multiple workers) instead of the
# single-threaded Django dev server. This is the realistic target for
# load/concurrency testing (e.g. the Gatling Dos simulation):
# the dev server used by `run` serializes requests and will show load-test
# failures that are really about itself, not about the app's real capacity.
run-prod: stop-db
	podman-compose -f docker-compose.yml -f nginx-uwsgi/docker-compose.yml up --build

# Upgrades all dependencies (asks for confirmation, logs changes to upgraded.md)
upgrade:
	bash upgrade.sh

# Creates sample data in the running `run-prod` stack: the organization RAP, the user
# julia (password julia123) and 10 petitions. If the database already has petitions it
# does nothing, because gen_pet always names them "Petition 0", "Petition 1"... and a
# second run would fail on the duplicated slug. To start from scratch delete the data with:
#   podman-compose -f docker-compose.yml -f nginx-uwsgi/docker-compose.yml down -v
# Use `docker` instead of `podman` if you use Docker.
MANAGE = podman exec pytitions_web_1 python3 pytition/manage.py
populate:
	@n=$$($(MANAGE) shell -c "from petition.models import Petition; print(Petition.objects.count())" | tail -1); \
	if [ "$$n" != "0" ]; then echo "The database already has $$n petitions: nothing to do."; exit 0; fi; \
	$(MANAGE) gen_orga RAP; \
	$(MANAGE) gen_user julia julia123 -fn Julia -ln Test; \
	$(MANAGE) join_org julia RAP; \
	$(MANAGE) gen_pet --user julia -n 10 && echo "Done: user julia / julia123, 10 petitions."

.PHONY: run install db migrate stop-db run-prod upgrade populate
