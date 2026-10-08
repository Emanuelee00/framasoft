To use pytition with nginx/uwsgi, you need to do:

In the pytition main directory

`docker-compose -f docker-compose.yml -f nginx-uwsgi/docker-compose.yml up --build`

## First start: the database is empty

`make run-prod` (from `pytitions/`) builds the images, creates the tables (`migrate`) and starts the site on
http://127.0.0.1:8000. The tables are created but there is **no data**: no user, no organization, no petition.
To create sample data (organization `RAP`, user `julia` / `julia123` and 10 petitions), with the stack running,
from `pytitions/`:

```bash
make populate
```

It does nothing if the database already has petitions. To create the admin user for `/admin/` (interactive):

```bash
podman exec -it pytitions_web_1 python3 pytition/manage.py createsuperuser
```

To run the commands one by one (`gen_orga`, `gen_user`, `join_org`, `gen_pet`) see the `populate` target of the `makefile`.

Use `docker exec` instead of `podman exec` (and `docker compose` instead of `podman-compose`) if you use Docker.

## E-mails

Signing a petition or creating an account sends an e-mail. The stack sends them to the `maildev`
container (`smtp` service), so nothing leaves your machine: read them at http://127.0.0.1:8080.
The setting is in `pytition/pytition/settings/docker.py`; without it Django tries `localhost:25`, which does
not exist in the container, and the signature ends with an HTTP 500 (after being saved).

## Stop and start again

* Stop: `Ctrl+C`, or `podman stop pytitions_web_1 pytitions_db_1 pytitions_smtp_1`. The data stays.
* Start again: `make run-prod`.
* Delete everything, data included: `podman-compose -f docker-compose.yml -f nginx-uwsgi/docker-compose.yml down -v`.

## Client IP and the per-IP signature limit

nginx passes the visitor's address to the application as `REMOTE_ADDR` (`uwsgi_params`), and the
application uses it for the limit of 5 signatures per petition and per day. Keep
`PYTITION_TRUSTED_PROXY_COUNT` at 0 with this stack: nginx is the first proxy and does not set
`X-Forwarded-For`, so trusting that header would let any client pick its own address.

* Load tests run from one machine, so every request has the same address and the limit stops them
  after 5 signatures. For benchmarks only, start the stack with a higher limit:
  `SIGNATURE_THROTTLE=1000000 make run-prod` (and add `SIGNATURE_THROTTLE` to the `environment` of the
  `web` service).
* Rootless podman and Docker Desktop can replace the visitor's address with the address of the
  container network. In production, check in the nginx access log that real client addresses arrive.
* If another reverse proxy or a CDN sits in front of this nginx, make that proxy set `X-Forwarded-For`
  and set `PYTITION_TRUSTED_PROXY_COUNT` to the number of proxies in front of the application.

## Django version of this stack

The image installs `requirements.txt` (Django 4.2, the version of Framasoft's `frama` branch). The
`uv` environment (`uv.lock`) uses Django 5.2. The test suite passes on both.
