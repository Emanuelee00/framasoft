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
| Server | `make run-prod` stack: nginx + uWSGI (Python 3.11, Django 5.2.18) + PostgreSQL |
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
| nginx + uWSGI, 32 workers, backlog 1024 (Django 5.2) | 1000 users in 1 s | 506 / 1000 | 50.6% | 3.1 | 4.5 | 4.8 |
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
   Raising those two values and repeating the test has **not been done yet**, so this is the most
   likely cause but is not proven.
4. **32 workers with backlog 100 is an outlier**: more OK responses (5851) but very slow
   (p50 16 s, p95 55 s, 4.6% timeouts). Not a configuration to use.
5. **Burst of 1000 users in 1 s**: the new stack answers 506 requests in at most 4.8 s and closes the
   other 494 before a response; the development server serves 937, but slowly (95th percentile 54 s),
   and 63 connections time out after 10 s. At 30000 users in 30 s the development server serves 345
   requests (1.1%; 29350 connection timeouts), the new stack 1463 to 5851 (4.9% to 19.5%).

## Limits of this benchmark

- One run per configuration: no repetitions, no measure of variance. Differences of a few
  hundred requests between neighbouring rows may be noise.
- Gatling and the server share 4 cores and the network stack of one machine. Port 8000 is
  published through rootless podman's port forwarding, which can also be a limit (not measured).
- The old and new setups differ in Django version (4.2.13 vs 5.2.18) **and** in server
  (`runserver` vs nginx + uWSGI), so the comparison does not isolate the effect of Django.
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
