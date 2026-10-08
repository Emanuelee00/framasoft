# TODO

Gaps found while load-testing this project with Gatling, organized by topic.

## `make run-prod` is currently broken (blocking, fix before load-testing)

- [ ] `nginx-uwsgi/Dockerfile_uwsgi` builds `FROM tiangolo/uwsgi-nginx:python3.7`.
  Python 3.7 is too old for this project's `Django~=4.2.0` requirement (Django
  4.2 needs Python 3.8+), so `pip install -r requirements_dev.txt` fails during
  the image build with `No matching distribution found for Django~=4.2.0` —
  pip can only see Django releases up to 3.2.x on that Python version.
  `make run-prod` therefore fails at the build step every time, before the
  stack ever starts. Needs the base image bumped to a Python version that
  satisfies current `requirements.txt` (e.g. `tiangolo/uwsgi-nginx:python3.11`,
  or a different base entirely since that image hasn't been updated in years),
  then re-check the rest of `Dockerfile_uwsgi`/`uwsgi.ini` still applies.
- [ ] (Environment-only, not a repo change) building any image with Podman on
  this machine also needed `~/.config/containers/registries.conf` set to
  `unqualified-search-registries = ["docker.io"]` — the system config listed 3
  registries, which makes Podman prompt interactively (fails non-interactively)
  to resolve short image names like `postgres` or `tiangolo/uwsgi-nginx`. Not
  something to fix in this repo, just worth knowing if `run-prod` still fails
  on a fresh machine.

## App server concurrency

- [ ] `nginx-uwsgi/uwsgi.ini` has no `processes`, `threads`, or `async` directive.
  Without them uWSGI defaults to **1 process / 1 thread / synchronous**, so the
  "production" nginx+uWSGI stack currently handles one request at a time, barely
  better than `manage.py runserver`. Add something like:
  ```ini
  processes = 4
  threads = 2
  enable-threads = true
  ```
  (processes ≈ number of CPU cores available to the container).
- [ ] `nginx.conf` has `worker_processes 1`. Fine for nginx itself (event-driven,
  one worker handles many connections), but confirm it's not also a bottleneck
  once uWSGI concurrency is fixed.
- [ ] Decide early whether to stay on WSGI (uWSGI/gunicorn) or move to ASGI
  (uvicorn) if any async views/websockets are ever needed — changes the whole
  server choice.

## Load testing setup

- [ ] `make run` (Django dev server) and `make run-prod` (docker-compose +
  nginx-uwsgi) must never run at the same time: both want port 8000 and their
  own Postgres on port 5432. `run-prod` now stops the standalone `pytition-db`
  container first, but there's no corresponding guard the other way around.
- [ ] Load-testing against `manage.py runserver` produces misleading results
  (timeouts/connection errors that reflect the dev server's single-thread
  limit, not real app capacity). Always test against `run-prod`.
- [ ] `choose_test.py` / `Dos.scala` only test the `GET /` endpoint. Consider
  adding scenarios for authenticated/write paths (the ones that hit the DB and
  are more likely to reveal real bottlenecks).

## Caching

- [ ] No cache layer (Redis/Memcached). Every request currently hits
  Postgres directly; a cache would reduce DB load and likely raise the
  concurrency ceiling found by the load tests.

## Background jobs / async work

- [ ] No task queue (Celery/RQ). Any slow operation (email sending, exports,
  etc.) currently runs inline in the request/response cycle, which will block
  a worker under load. `EMAIL_BACKEND = mailer` in the compose file suggests
  there may already be slow I/O (sending email) done synchronously.

## Database

- [ ] No connection pooling (e.g. PgBouncer) in front of Postgres. Under the
  concurrency levels tested (thousands of workers), raw per-worker DB
  connections can exhaust Postgres's `max_connections` before the app layer
  even becomes the bottleneck.

## Secrets / config

- [ ] `makefile`'s `pytition/pytition/settings/local.py` target generates
  `DEBUG = True` and a plaintext DB password (`postgres`/`postgres`) — fine for
  local dev, but make sure nothing based on this file path is ever reused for
  a real deployment.

## Observability

- [ ] No metrics/monitoring (Prometheus/Grafana) or centralized logging.
  Right now the only way to see what breaks under load is reading raw Gatling
  reports and `ps`/`free` by hand — fine for this exercise, not for production.

## CI

- [ ] `Jenkinsfile` exists and runs tests, but does not run any load/capacity
  test (e.g. the Gatling `Dos` simulation) — consider adding a lightweight
  capacity check to catch regressions before they reach `run-prod`.
