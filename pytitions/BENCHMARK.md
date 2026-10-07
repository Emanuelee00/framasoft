# Benchmark: uWSGI workers and socket backlog

Load test of the home page (`GET /`) with Gatling, comparing the number of uWSGI
workers (1 to 32) with the default socket backlog (100) and a larger one (1024),
and comparing the result with the original Django 4.2 development server.

**Status: single run per configuration, on a laptop-class machine that also runs
the load generator. Use the numbers to compare configurations with each other,
not as absolute capacity figures. See [Limits of this benchmark](#limits-of-this-benchmark).**

## Setup

| | |
|---|---|
| Machine | Intel Core i5-6500 (4 cores), 7.6 GiB RAM, Fedora, rootless podman 5.8.7 |
| Load generator | Gatling `example.Dos` (Gatling-Performance-Test-starter), on the **same machine** |
| Request | `GET /` only; counted as OK for status 200 or 304 |
| Server | `make run-prod` stack: nginx + uWSGI (Python 3.11, Django 4.2.30, installed from `requirements.txt` by `Dockerfile_uwsgi`) + PostgreSQL |
| uWSGI | `UWSGI_PROCESSES` = 1 to 32, `UWSGI_CHEAPER=0` (all workers always running), `UWSGI_LISTEN` = 100 or 1024 |
| Load | 30000 users ramped over 30 s, i.e. 1000 new requests per second for 30 s |
| Between runs | whole stack removed and recreated, fresh database |

## Results: workers and backlog (1000 requests/s for 30 s)

Percentiles are computed on the OK responses only.

| Workers | Backlog | OK / 30000 | OK % | p50 (s) | p95 (s) | p99 (s) | closed before response (a) | HTTP error status | timeout | other |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 100 | 1463 | 4.9% | 4.3 | 36.9 | 37.9 | 0.1% | 95.0% | 0.0% | 0.0% |
| 1 | 1024 | 1946 | 6.5% | 9.5 | 11.8 | 12.3 | 93.5% | 0.0% | 0.0% | 0.0% |
| 2 | 100 | 1729 | 5.8% | 3.1 | 10.9 | 11.7 | 10.8% | 83.4% | 0.0% | 0.0% |
| 2 | 1024 | 2724 | 9.1% | 6.0 | 7.7 | 8.0 | 90.9% | 0.0% | 0.0% | 0.0% |
| 4 | 100 | 2147 | 7.2% | 3.4 | 8.0 | 8.4 | 6.5% | 86.3% | 0.0% | 0.0% |
| 4 | 1024 | 3365 | 11.2% | 4.4 | 8.0 | 8.2 | 88.8% | 0.0% | 0.0% | 0.0% |
| 8 | 100 | 2598 | 8.7% | 3.8 | 13.9 | 14.5 | 16.6% | 74.8% | 0.0% | 0.0% |
| 8 | 1024 | 3136 | 10.5% | 4.5 | 7.6 | 7.9 | 89.5% | 0.0% | 0.0% | 0.0% |
| 16 | 100 | 2978 | 9.9% | 6.4 | 14.4 | 14.9 | 19.8% | 70.2% | 0.0% | 0.0% |
| 16 | 1024 | 3640 | 12.1% | 4.5 | 5.2 | 5.3 | 87.9% | 0.0% | 0.0% | 0.0% |
| 32 | 100 | 5851 | 19.5% | 16.1 | 55.2 | 59.1 | 26.4% | 49.5% | 4.6% | 0.0% |
| 32 | 1024 | 3284 | 10.9% | 4.7 | 6.3 | 7.0 | 89.1% | 0.0% | 0.0% | 0.0% |

(a) Category "never reached the server" of `analyze_results.py`: it groups `Premature close`
and similar errors, i.e. connections that were closed before an answer arrived.
"HTTP error status" are answers that were not 200 or 304 (502 in the run that was checked by hand).

## Results: comparison with the original development server

The "old" setup is the same application code with Django 4.2.13 (versions from `pdm.lock`), started
with `manage.py runserver` as `make run` does, against a fresh database. It has no worker setting.

| Setup | Load | OK | OK % | p50 (s) | p95 (s) | max (s) |
|---|---|---:|---:|---:|---:|---:|
| nginx + uWSGI, 32 workers, backlog 1024 (Django 4.2.30) | 1000 users in 1 s | 506 / 1000 | 50.6% | 3.1 | 4.5 | 4.8 |
| Django 4.2.13 `runserver` (no workers) | 1000 users in 1 s | 937 / 1000 | 93.7% | 6.6 | 54.2 | 56.9 |
| Django 4.2.13 `runserver` (no workers) | 30000 users in 30 s | 345 / 30000 | 1.1% | 2.8 | 41.5 | 59.5 |

## What the numbers show

1. **The larger backlog helps.** With backlog 1024, up to 16 workers, more requests succeed than
   with 100 (for example 4 workers: 3365 vs 2147) and the 95th percentile is lower or equal
   (16 workers: 5.2 s vs 14.4 s). With backlog 100, answers with an error status are 50% to 95% of
   all requests; with 1024 there are none, the failures become connections closed before a response.
   The error status is probably uWSGI's full queue seen through nginx, but the cause was not checked.
2. **More workers help up to about the number of cores.** From 1 to 4 workers the successful
   requests go from 1946 to 3365 (backlog 1024); from 4 to 32 they stay between 3136 and 3640.
   The machine has 4 cores and the load generator uses part of them.
3. **Between 80% and 95% of the requests fail in every configuration**, so this test does not
   reach the capacity of uWSGI. The nginx log of a 1000-user burst shows
   `1024 worker_connections are not enough, reusing connections`, and `nginx-uwsgi/nginx.conf`
   sets `worker_processes 1` and `worker_connections 1024`. Each proxied request uses two
   connections (client and uWSGI), so about 500 simultaneous requests fill nginx.
   Raising those two values changes the picture, see the second series below.
4. **32 workers with backlog 100 is an outlier**: more OK responses (5851) but very slow
   (p50 16 s, p95 55 s, 4.6% timeouts). Not a configuration to use.
5. **Burst of 1000 users in 1 s**: the new stack answers 506 requests in at most 4.8 s and closes the
   other 494 before a response; the development server serves 937, but slowly (95th percentile 54 s),
   and 63 connections time out after 10 s. At 30000 users in 30 s the development server serves 345
   requests (1.1%; 29350 connection timeouts), the new stack 1463 to 5851 (4.9% to 19.5%).

## Second series: nginx limits raised

The first series suggested that nginx (`worker_processes 1`, `worker_connections 1024`) was the
limit. The same test was repeated (backlog 1024, `UWSGI_CHEAPER=0`, 30000 users in 30 s) with
`worker_processes auto` (4 on this machine) and `worker_connections 8192` in `nginx-uwsgi/nginx.conf`.
"Before" is the backlog 1024 row of the first series.

| Workers | OK before | OK after | OK % after | p50 before / after (s) | p95 before / after (s) | HTTP 502 after | closed before response after |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1946 | 3144 | 10.5% | 9.5 / 31.4 | 11.8 / 48.3 | 89.5% | 0.0% |
| 2 | 2724 | 3917 | 13.1% | 6.0 / 23.0 | 7.7 / 46.4 | 86.0% | 0.9% |
| 4 | 3365 | 3157 | 10.5% | 4.4 / 18.1 | 8.0 / 20.3 | 76.6% | 12.9% |
| 8 | 3136 | 3858 | 12.9% | 4.5 / 16.5 | 7.6 / 32.0 | 64.2% | 23.0% |
| 16 | 3640 | 4217 | 14.1% | 4.5 / 14.2 | 5.2 / 24.3 | 66.4% | 19.5% |
| 32 | 3284 | 5348 | 17.8% | 4.7 / 21.4 | 6.3 / 36.2 | 63.8% | 18.4% |

What changed:

- More requests succeed in 5 of 6 cases (for example 32 workers: 3284 to 5348; 1 worker: 1946 to 3144);
  with 4 workers it is the same within noise (3365 to 3157). The success rate stays between 10% and 18%.
- The failures changed kind: connections closed by nginx are replaced by **HTTP 502** answers
  (64% to 90% of the requests). nginx now accepts every connection, and the 502 are most likely
  uWSGI's queue (backlog 1024) being full; this was not checked in the nginx log.
- The latency of the successful requests is much higher (p50 14 s to 31 s, before 4 s to 10 s),
  because accepted requests wait a long time for a free worker.

So raising the nginx limits moves the bottleneck to uWSGI (workers and queue) but, on this machine, does
not make the stack serve many more requests. It was **not** committed to the branch: the limits
are the original ones. To repeat the series, set the two values above and rebuild
(`make run-prod` does it with `--build`).

## Limits of this benchmark

- One run per configuration (30 runs in total, no repetitions): no repetitions, no measure of variance. Differences of a few
  hundred requests between neighbouring rows may be noise.
- Gatling and the server share 4 cores and the network stack of one machine. Port 8000 is
  published through rootless podman's port forwarding, which can also be a limit (not measured).
- The old and new setups differ mainly in the server (`runserver` vs nginx + uWSGI). Django is
  4.2.13 (`pdm.lock`) vs 4.2.30 (`requirements.txt`, same minor series) and the other packages
  differ too, so the comparison is not a pure server comparison either.
- `UWSGI_CHEAPER=0` was used so that "N workers" means N running workers. The default of the stack
  is `UWSGI_CHEAPER=4`.
- Only the home page was requested; pages that write to the database may behave differently.

## How to reproduce

```
# stack (from pytitions/), for example 8 workers and backlog 1024
UWSGI_PROCESSES=8 UWSGI_CHEAPER=0 UWSGI_LISTEN=1024 make run-prod

# load (from Gatling-Performance-Test-starter/): 1000 requests/s for 30 s
mvn gatling:test -Dgatling.simulationClass=example.Dos -Dusers=30000 -Dseconds=30
python3 analyze_results.py
```

For the old setup use a virtualenv with the versions of `pdm.lock` (Django 4.2.13), then run
`manage.py runserver 127.0.0.1:8000` and the same Gatling command.

## Comparison with branch `modernized_plus_minimalist`

The same tests were repeated on the branch `origin/modernized_plus_minimalist` (commit `cfe6805`),
to see if its changes improve the results of this branch (`emanuele`). Same machine, same
commands, same load; the 18 tests with nginx + uWSGI and the 2 with `runserver` were all repeated.
The files of the stack (`nginx-uwsgi/`, `Dockerfile`, `requirements.txt`) are identical in both
branches, so the images and the uWSGI settings are the same. The application code differs:

- `create_signature`: the IP of the signer is hashed with HMAC-SHA256 (`hash_ip`) instead of
  `make_password`, and `cron_to_schedule` is changed with one `UPDATE` instead of `petition.save()`;
- `cron` command and `base.py` (`SIGNATURE_THROTTLE` raised to 5000000000) changed;
- `docker-compose.yml` and a `Makefile` that runs `docker compose up`.

### Workers and backlog (1000 requests/s for 30 s)

| Workers | Backlog | OK emanuele | OK colleague | diff | p50 (s) emanuele / colleague | p95 (s) emanuele / colleague |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 100 | 1463 | 1294 | -12% | 4.3 / 2.8 | 36.9 / 34.5 |
| 1 | 1024 | 1946 | 1915 | -2% | 9.5 / 9.9 | 11.8 / 11.8 |
| 2 | 100 | 1729 | 1954 | +13% | 3.1 / 3.0 | 10.9 / 11.0 |
| 2 | 1024 | 2724 | 2893 | +6% | 6.0 / 6.0 | 7.7 / 6.9 |
| 4 | 100 | 2147 | 2407 | +12% | 3.4 / 2.7 | 8.0 / 8.6 |
| 4 | 1024 | 3365 | 3458 | +3% | 4.4 / 4.5 | 8.0 / 6.0 |
| 8 | 100 | 2598 | 2898 | +12% | 3.8 / 3.2 | 13.9 / 9.7 |
| 8 | 1024 | 3136 | 3532 | +13% | 4.5 / 4.8 | 7.6 / 5.6 |
| 16 | 100 | 2978 | 3304 | +11% | 6.4 / 3.0 | 14.4 / 10.2 |
| 16 | 1024 | 3640 | 3054 | -16% | 4.5 / 5.3 | 5.2 / 6.2 |
| 32 | 100 | 5851 | 4858 | -17% | 16.1 / 17.2 | 55.2 / 57.1 |
| 32 | 1024 | 3284 | 2656 | -19% | 4.7 / 4.6 | 6.3 / 14.5 |

### Other series

| Series | Workers | OK emanuele | OK colleague | diff | p50 (s) e / c | p95 (s) e / c |
|---|---:|---:|---:|---:|---:|---:|
| burst 1000 users in 1 s, backlog 1024 | 32 | 506 / 1000 | 486 / 1000 | -4% | 3.1 / 3.5 | 4.5 / 4.7 |
| nginx raised, backlog 1024 | 1 | 3144 | 3263 | +4% | 31.4 / 35.2 | 48.3 / 53.3 |
| nginx raised, backlog 1024 | 2 | 3917 | 3999 | +2% | 23.0 / 21.1 | 46.4 / 43.0 |
| nginx raised, backlog 1024 | 4 | 3157 | 3492 | +11% | 18.1 / 17.3 | 20.3 / 21.8 |
| nginx raised, backlog 1024 | 8 | 3858 | 3834 | -1% | 16.5 / 13.9 | 32.0 / 20.0 |
| nginx raised, backlog 1024 | 16 | 4217 | 4220 | +0% | 14.2 / 13.4 | 24.3 / 20.9 |
| nginx raised, backlog 1024 | 32 | 5348 | 4414 | -17% | 21.4 / 14.0 | 36.2 / 22.9 |
| `runserver` Django 4.2.13, 1000 users in 1 s | - | 937 | 863 | -8% | 6.6 / 5.8 | 54.2 / 29.5 |
| `runserver` Django 4.2.13, 30000 users in 30 s | - | 345 | 142 | -59% | 2.8 / 2.3 | 41.5 / 58.5 |

### Result

- **No measurable difference.** The change in successful requests over the 18 runs with nginx + uWSGI
  has mean +0.1% and median +2.4%, from -19% to +13%, better in 11 runs and worse in 7. This is
  the same size as the variation between neighbouring rows of a single series, so it is noise.
- **This is expected.** The load only requests the home page (`GET /`), and none of the code
  changed in the other branch is run by that request: it is on the path that creates a signature.
  These tests cannot show its effect, neither for better nor for worse.
- The `runserver` run with 30000 users (345 vs 142 successful requests) has a large relative
  difference, but on very small numbers from a server that is saturated; it is not a reliable result.
- The signature code is measured in the next section.

## Signing petitions (POST): comparison of the two branches

The home-page tests above cannot show the effect of the changes in `modernized_plus_minimalist`,
because they are in the code that creates a signature. This series tests that code.

**Test.** New Gatling simulation `example.Sign` (file `src/test/scala/example/Sign.scala` of
`Gatling-Performance-Test-starter`). Each virtual user loads a petition page (to get the CSRF
token) and then POSTs the signature form to `/petition/<id>/sign`; success is the 302 answer.
Users arrive at a constant rate for 30 s, on 3 sample petitions (`gen_pet`).

- Stack: nginx + uWSGI with 8 workers, `UWSGI_CHEAPER=0`, backlog 1024, nginx limits unchanged;
  fresh database and sample data for every run.
- Every user sends its own `X-Forwarded-For`, so the per-IP signature limit (5 in this branch,
  disabled in the other) does not influence the result.
- E-mails are dropped (`dummy` backend, settings file outside the repositories): in the stack
  the SMTP backend points to `localhost:25`, which does not exist in the container, and the
  signature request would end with HTTP 500 after saving the signature.
- "Signatures saved" is the number of rows in the database after the run.

| Offered load | Signatures saved: emanuele | colleague | Sign p50 (s): emanuele / colleague | Sign p95 (s): emanuele / colleague | users that failed before signing: emanuele / colleague |
|---|---:|---:|---:|---:|---:|
| 10/s (300 users) | 300 | 300 | 1.1 / 0.04 | 2.4 / 0.35 | 0 / 0 |
| 25/s (750 users) | 749 | 750 | 16.8 / 0.03 | 23.5 / 0.39 | 1 / 0 |
| 50/s (1500 users) | 754 | 1500 | 20.4 / 0.74 | 24.0 / 3.9 | 732 / 0 |
| 100/s (3000 users) | 740 | 1563 | 17.6 / 4.9 | 32.0 / 6.5 | 2158 / 1264 |
| 200/s (6000 users) | 719 | 1263 | 20.1 / 5.3 | 23.5 / 8.2 | 5020 / 4146 |

What the numbers show:

- **At low load the signature request is about 29 times faster** in the other branch:
  p50 of 1.10 s against 0.04 s at 10 signatures/s, where nothing is queued. The signature stored by
  this branch carries a `bcrypt_sha256` hash of the IP (`make_password`, checked by hand), which is slow by
  design; the other branch uses HMAC-SHA256. The size of the difference matches this explanation,
  but the time spent in the hash was not measured separately.
- **Capacity is about twice as high.** This branch saves about 720 to 750 signatures per run
  from 25/s up, however high the load; the other one saves 1500 at 50/s and 1563 at 100/s.
  Above those loads both queue up and the latency of the signature goes to several seconds,
  and users start to fail already when loading the petition page.
- At 200/s both are overloaded (719 and 1263 signatures saved out of 6000 users).
- The change of `petition.save()` into a conditional `UPDATE` was not measured separately from the
  hash, so this test cannot tell how much each change contributes.

Limits: one run per point; Gatling runs on the same 4-core machine; only 8 workers were tried;
e-mail sending is not included, so a real instance is slower than these numbers.

To repeat it, create the sample data (`gen_orga`, `gen_user`, `join_org`, `gen_pet -n 3`) and run
`mvn gatling:test -Dgatling.simulationClass=example.Sign -Drate=50 -Dseconds=30`.
