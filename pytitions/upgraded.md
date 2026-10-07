## 2026-10-07 00:29:48 (starting from commit ea34cd7)

- alabaster: 0.7.13 / 0.7.16 -> 1.0.0
- alt-profanity-check: 1.3.2 / 1.6.1 / 1.7.2 / 1.9.1 -> 1.7.2 / 1.9.1
- asgiref: 3.11.1 / 3.12.1 / 3.8.1 -> 3.12.1
- backports-zoneinfo: 0.2.1 -> -
- beautifulsoup4: 4.6.3 -> 4.15.0
- contourpy: 1.1.1 / 1.3.0 / 1.3.2 / 1.3.3 / 1.4.0 -> 1.3.2 / 1.3.3 / 1.4.0
- django: 4.2.30 -> 5.2.18
- django-colorfield: 0.10.1 -> 0.14.0
- django-formtools: 2.2 -> 2.7
- django-mailer: 2.3 -> 2.3.2
- django-phonenumber-field: 6.3.0 -> 8.5.0
- django-tinymce: 3.6.1 -> 5.0.0
- django-widget-tweaks: 1.4.3 -> 1.5.1
- docutils: 0.20.1 / 0.21.2 -> 0.21.2 / 0.22.4
- fonttools: 4.57.0 / 4.60.2 / 4.65.0 / 4.66.1 -> 4.65.0 / 4.66.1
- idna: 3.15 / 3.20 -> 3.20
- imagesize: 1.5.0 / 2.0.1 -> 2.0.1
- importlib-metadata: 8.5.0 / 8.7.1 -> -
- importlib-resources: 6.4.5 / 6.5.2 -> -
- jinja2: 3.0.3 -> 3.1.6
- joblib: 1.4.2 / 1.5.1 / 1.6.0 -> 1.5.1 / 1.6.0
- kiwisolver: 1.4.7 / 1.5.1 -> 1.5.1
- markupsafe: 2.1.5 / 3.0.4 -> 3.0.4
- matplotlib: 3.10.9 / 3.11.2 / 3.7.5 / 3.9.4 -> 3.10.9 / 3.11.2
- numpy: 1.24.4 / 2.0.2 / 2.2.6 / 2.4.6 / 2.5.3 -> 2.2.6 / 2.4.6 / 2.5.3
- packaging: 26.2 / 26.3 -> 26.3
- pillow: 10.4.0 / 11.3.0 / 12.3.0 -> 12.3.0
- psycopg: 3.1.19 -> 3.3.6
- psycopg-binary: 3.1.19 -> 3.3.6
- pygments: 2.19.2 / 2.21.0 -> 2.21.0
- pyparsing: 3.1.4 / 3.3.3 -> 3.3.3
- pytz: 2026.5 -> -
- requests: 2.32.4 / 2.32.5 / 2.34.2 -> 2.34.2
- roman-numerals: - -> 4.1.0
- scikit-learn: 1.3.2 / 1.6.1 / 1.7.2 / 1.9.1 -> 1.7.2 / 1.9.1
- scipy: 1.10.1 / 1.13.1 / 1.15.3 / 1.17.1 / 1.18.1 -> 1.15.3 / 1.17.1 / 1.18.1
- setuptools: 75.3.4 / 82.0.1 / 84.0.0 -> 80.10.2
- soupsieve: - -> 2.10
- sphinx: 7.1.2 / 7.3.7 -> 8.1.3 / 9.0.4 / 9.1.0
- sphinxcontrib-applehelp: 1.0.4 / 2.0.0 -> 2.0.0
- sphinxcontrib-devhelp: 1.0.2 / 2.0.0 -> 2.0.0
- sphinxcontrib-htmlhelp: 2.0.1 / 2.1.0 -> 2.1.0
- sphinxcontrib-qthelp: 1.0.3 / 2.0.0 -> 2.0.0
- sphinxcontrib-serializinghtml: 1.1.5 / 2.0.0 -> 2.0.0
- sqlparse: 0.5.5 / 0.6.0 -> 0.6.0
- threadpoolctl: 3.5.0 / 3.7.0 -> 3.7.0
- typing-extensions: 4.13.2 / 4.16.0 -> 4.16.0
- urllib3: 2.2.3 / 2.6.3 / 2.8.0 -> 2.8.0
- zipp: 3.20.2 / 3.23.1 -> -

Rollback: `git checkout ea34cd7 -- uv.lock && uv sync --all-groups --no-install-package uwsgi`

---

## 2026-10-07 14:47:28 (starting from commit 47e949a)

- tomli: 2.4.1 -> 2.5.0

Rollback: `git checkout 47e949a -- uv.lock pyproject.toml && uv sync --all-groups --no-install-package uwsgi`
