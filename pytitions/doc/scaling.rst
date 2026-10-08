How to scale Pytition
*********************

This page explains what limits the number of signatures per second a Pytition instance can
handle, which settings to use for a petition that goes viral, and what to do next when a
single server is not enough.

The critical path is the signature: ``POST /petition/<id>/sign`` (form validation, per IP
address throttle, insert, confirmation email), then the click on the confirmation link
(``GET /petition/<id>/confirm/<hash>``). Most of the other traffic is the petition page itself.

Measurements
============

Bench: one petition with 100,000 signatures (10% unconfirmed), gunicorn with 4 sync workers,
PostgreSQL 16 in Docker, Apple M1 Pro (8 cores, shared with other workloads), console email
backend. 16 concurrent clients sending requests back to back for 30 s per scenario; each
value is the median of 3 runs. The machine was shared with other workloads: from one run to
another, the throughput varied by up to a factor 2, so only the order of magnitude matters.

================================ ============== ============== ===============
Scenario                          Before         After          After + persistent DB connections
================================ ============== ============== ===============
Signatures per second             9              116            304
``POST sign`` p50 / p95 (ms)      1657 / 2089    121 / 252      45 / 81
Petition page per second          76             143            385
Petition page p50 / p95 (ms)      200 / 299      100 / 167      42 / 63
Confirmations per second          41             78             117
Confirmation p50 / p95 (ms)       390 / 558      202 / 337      131 / 204
SQL queries per signature         11             7              7
================================ ============== ============== ===============

The main gains come from:

* hashing the signer IP address with HMAC-SHA256 instead of bcrypt: about 250 ms of CPU
  per signature before, a few microseconds now;
* indexes on the ``petition_signature`` table for the queries run at each signature and
  confirmation (throttle, "already signed" check, confirmation hash);
* no more full ``Petition`` save at each signature (only ``cron_to_schedule`` is updated,
  when it changes);
* the number of signatures displayed on pages and lists is cached for a short time.

With the default database settings (one new PostgreSQL connection per request), from about
170 requests per second some connections were refused in our bench: persistent connections
(see below) fix it and double the throughput.

Rough capacity on this machine: 30 to 75 signatures per second per worker process
(including the database work), the higher value with persistent database connections.

Recommended configuration
=========================

Database connections
--------------------

Keep the database connections open between requests, with a health check:

.. code-block:: python

    DATABASES = {
        'default': {
            # ...
            'CONN_MAX_AGE': 60,
            'CONN_HEALTH_CHECKS': True,
        }
    }

The value can also come from the environment:
:data:`~pytition.settings.base.DATABASE_CONN_MAX_AGE` reads ``DATABASE_CONN_MAX_AGE``
(``0`` by default, which keeps the previous behaviour). The Docker image applies it to its
database; in your ``config.py``, write ``'CONN_MAX_AGE': DATABASE_CONN_MAX_AGE`` in
``DATABASES`` and set for instance ``DATABASE_CONN_MAX_AGE=60`` in the uwsgi environment
(``env = DATABASE_CONN_MAX_AGE=60``).

Each uwsgi process then keeps one connection: make sure that PostgreSQL ``max_connections``
is larger than the total number of processes (of all instances) plus the maintenance
connections.

Mail queue
----------

Set :data:`~pytition.settings.base.USE_MAIL_QUEUE` to ``True`` (see :doc:`configuration`):
the confirmation email is then written to the database and sent by the uwsgi timer (or by a
cron job), so a slow or unavailable SMTP server no longer slows down or breaks the signature.

* The queue is processed every ``UWSGI_WAIT_FOR_MAIL_SEND_IN_S`` seconds (10 by default). At
  100 signatures per second, that is about 1,000 emails per cycle: use a local MTA (postfix)
  that accepts them quickly and relays them, and check its rate limits.
* ``purge_mail_log`` only removes the logs of successfully sent emails older than
  ``UWSGI_NB_DAYS_TO_KEEP`` days. The queue tables contain the email address and first name
  of the signers: keep this retention short.
* Calls to the newsletter of a petition (HTTP or SMTP) have a timeout and never make a
  signature fail.

uwsgi
-----

Example for a 4 core server:

.. code-block:: ini

    [uwsgi]
    # ...
    master = true
    processes = 8          # start with about 2 per core, then adjust with a load test
    threads = 1
    harakiri = 30          # kill a request stuck for more than 30 s
    max-requests = 5000    # recycle workers regularly
    listen = 1024          # accept bursts instead of refusing connections

Client IP address
-----------------

The per IP address throttle (``SIGNATURE_THROTTLE`` signatures per
``SIGNATURE_THROTTLE_TIMING`` seconds) needs the real client address.
:data:`~pytition.settings.base.PYTITION_TRUSTED_PROXY_COUNT` is the number of reverse proxies
in front of Pytition that append to ``X-Forwarded-For``:

* ``0`` (default): ``REMOTE_ADDR`` is used. This is the right value with the documented setup
  (nginx with ``uwsgi_pass``).
* ``1``: one proxy (for instance nginx with ``proxy_pass`` and
  ``proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for``).
* ``2`` or more: a CDN or a load balancer in front of nginx.

When the limit is reached, the signature is refused with a ``429`` status and a
``Retry-After`` header, and the moderation (``MODERATION_EMAIL``) receives one email per
petition and IP address per period. This deduplication uses the Django cache: with the
default local memory cache it is done per process (at most one email per uwsgi process).
Configure a shared cache (Memcached or Redis, see below) to get exactly one email.

IP address pseudonymisation key
-------------------------------

The IP address stored with a signature is an HMAC-SHA256 of the petition and of the address
(IPv6 addresses are reduced to their /64 network). The key comes from the
``SIGNATURE_IP_HMAC_KEY`` environment variable, or from ``SECRET_KEY`` when it is not set.
Use a dedicated random key, outside of the database:

.. code-block:: bash

    SIGNATURE_IP_HMAC_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')

Changing the key only resets the throttle counters, for at most
``SIGNATURE_THROTTLE_TIMING`` seconds.

Signature counter
-----------------

``SIGNATURE_COUNT_CACHE_TTL`` (30 seconds by default) is how long the number of signatures
displayed on petition pages and lists is cached. Set it to ``0`` to display the exact number
at each request.

Upgrading an existing instance
==============================

* **Indexes.** The migration ``0051_signature_indexes_gdpr`` changes the ``ipaddress``
  column to ``varchar(128)``, adds three nullable columns (quick) and creates 5 indexes on
  ``petition_signature``. On PostgreSQL, ``CREATE INDEX`` blocks the writes on the table while
  it runs. On a big table, either apply the migration during a maintenance window, or:

  1. print its SQL with ``python3 pytition/manage.py sqlmigrate petition 0051``;
  2. run the ``ALTER TABLE`` statements as they are, and the ``CREATE INDEX`` statements as
     ``CREATE INDEX CONCURRENTLY`` (outside of a transaction);
  3. mark the migration as applied with ``python3 pytition/manage.py migrate petition 0051 --fake``.

* **Throttle.** The IP addresses stored before the upgrade (bcrypt hashes) do not match the
  new HMAC values: during ``SIGNATURE_THROTTLE_TIMING`` seconds after the upgrade, an address
  can sign a few more times than the limit.

* **Cron.** The ``cron`` command now resets ``cron_to_schedule`` once a petition has been
  checked: a petition is checked again only after a new signature.

Going further
=============

These steps are not needed for the measured loads; they are listed in the order in which
they should be considered.

1. **Shared cache (Memcached or Redis)** as Django ``CACHES``: one throttle email per IP
   address for all processes, and a signature counter shared by all processes and servers.
   Needed as soon as there is more than one application server.
2. **PgBouncer** (transaction pooling) when the number of uwsgi processes of all servers gets
   close to ``max_connections``. With PgBouncer in transaction mode, keep ``CONN_MAX_AGE = 0``
   on the Django side, or use ``DISABLE_SERVER_SIDE_CURSORS = True``.
3. **nginx micro-cache** of the petition page for anonymous visitors (1 to 5 seconds,
   bypassed when a session cookie is present): the page is the bulk of the traffic of a
   viral petition. It needs care with the CSRF token of the signature form.
4. **Several application servers** behind a load balancer (with the shared cache, and
   ``PYTITION_TRUSTED_PROXY_COUNT`` set accordingly).
5. **PostgreSQL read replica** for the pages that only read (petition lists, counters),
   using a Django database router. The signature itself always needs the primary.
