# Correzioni

> Parte 1: correzioni e upgrade su Django 4.2. Parte 2 (in fondo): upgrade a Django 5.2.

Esito: la suite di test passa da **14 errori** (con le versioni bloccate) a **191/191 OK**, con tutte le dipendenze aggiornate all'ultima versione compatibile.

## 1. Codice

### Rilevatore di spam: numpy 2.4 non converte più array 1-D in float
`pytition/petition/spam_management/detectors/alt_profanity_check_detector.py:20`

<table><tr><th>Prima</th><th>Dopo</th></tr><tr><td>

```python
is_spam = predict_prob([content])
is_spam = float(is_spam)
```

</td><td>

```python
is_spam = predict_prob([content])
is_spam = float(is_spam[0])
```

</td></tr></table>

Causa: `predict_prob` restituisce un array con un solo elemento. `float()` su un array non 0-dimensionale era deprecato da numpy 1.25 ed è stato rimosso in numpy 2.4 (`TypeError: only 0-dimensional arrays can be converted to Python scalars`). Rompeva `test_edit_post_content_form*` e la modifica di qualunque petizione.

### PetitionTemplate non aveva il campo paper_signatures
`pytition/petition/models.py:699`

<table><tr><th>Prima</th><th>Dopo</th></tr><tr><td>

```python
paper_signatures_enabled = models.BooleanField(default=False)
```

</td><td>

```python
paper_signatures_enabled = models.BooleanField(default=False)
paper_signatures = models.IntegerField(default=0)
```

</td></tr></table>

Causa: form (`forms.py:119`) e view (`views.py:718`) usavano `template.paper_signatures`, ma il modello non lo aveva (bug già presente prima dell'aggiornamento, indipendente dalle versioni). Rompeva 14 test su `edit_template` e sui template di nuove petizioni. Aggiunta la migrazione `0050_petitiontemplate_paper_signatures.py`.

### Salvataggio template con numero di firme cartacee vuoto
`pytition/petition/views.py:718`

<table><tr><th>Prima</th><th>Dopo</th></tr><tr><td>

```python
template.paper_signatures = content_form.cleaned_data['paper_signatures']
```

</td><td>

```python
template.paper_signatures = content_form.cleaned_data['paper_signatures'] or 0
```

</td></tr></table>

Causa: il campo del form è `required=False`, quindi se omesso arriva `None` e il nuovo campo NOT NULL dava `IntegrityError`.

## 2. Gestione delle dipendenze

### pyproject.toml: via i pin esatti di pdm
`pyproject.toml`

<table><tr><th>Prima</th><th>Dopo</th></tr><tr><td>

```python
[tool.uv]
constraint-dependencies = ["alabaster==0.7.13", "django==4.2.13", "numpy==1.24.4", ... 70 pin]
```

</td><td>

```python
(sezione [tool.uv] rimossa)
# si usa solo: uv lock --upgrade && uv sync
```

</td></tr></table>

Le versioni bloccate erano solo la copia di pdm.lock. Ora il lock lo decide uv. I vincoli già presenti nelle dipendenze dirette (Django~=4.2, jinja2<3.1, beautifulsoup4~=4.6.3, psycopg 3.1.19 ecc.) restano.

## 3. Versioni cambiate

| Pacchetto | Prima (pdm.lock) | Dopo (uv upgrade) |
|---|---|---|
| alabaster | 0.7.13 | 0.7.16 |
| alt-profanity-check | 1.3.2 | 1.9.1 |
| asgiref | 3.8.1 | 3.12.1 |
| babel | 2.15.0 | 2.18.0 |
| bcrypt | 4.1.3 | 5.0.0 |
| certifi | 2024.6.2 | 2026.7.22 |
| charset-normalizer | 3.3.2 | 3.5.2 |
| cloudpickle | — | 3.1.2 |
| contourpy | 1.1.0 | 1.3.3 |
| django | 4.2.13 | 4.2.30 |
| django-maintenance-mode | 0.21.1 | 0.23.0 |
| docutils | 0.20.1 | 0.21.2 |
| fonttools | 4.57.0 | 4.66.1 |
| idna | 3.7 | 3.20 |
| imagesize | 1.4.1 | 2.0.1 |
| joblib | 1.4.2 | 1.6.0 |
| kiwisolver | 1.4.7 | 1.5.1 |
| lxml | 5.2.2 | 6.1.3 |
| lxml-html-clean | 0.1.1 | 0.4.5 |
| markupsafe | 2.1.5 | 3.0.4 |
| matplotlib | 3.7.5 | 3.11.2 |
| narwhals | — | 2.26.0 |
| numpy | 1.24.4 | 2.4.6 |
| packaging | 24.0 | 26.3 |
| phonenumbers | 8.13.38 | 9.0.40 |
| pillow | 10.3.0 | 12.3.0 |
| pygments | 2.18.0 | 2.21.0 |
| pyparsing | 3.1.4 | 3.3.3 |
| python-fsutil | 0.14.1 | 0.17.0 |
| requests | 2.32.3 | 2.34.2 |
| scikit-learn | 1.3.2 | 1.9.1 |
| scipy | 1.9.3 | 1.17.1 |
| setuptools | 75.3.2 | 84.0.0 |
| snowballstemmer | 2.2.0 | 3.1.1 |
| sphinx | 7.1.2 | 7.3.7 |
| sphinx-rtd-theme | 2.0.0 | 3.1.0 |
| sphinxcontrib-applehelp | 1.0.4 | 2.0.0 |
| sphinxcontrib-devhelp | 1.0.2 | 2.0.0 |
| sphinxcontrib-htmlhelp | 2.0.1 | 2.1.0 |
| sphinxcontrib-qthelp | 1.0.3 | 2.0.0 |
| sphinxcontrib-serializinghtml | 1.1.5 | 2.0.0 |
| sqlparse | 0.5.0 | 0.6.0 |
| threadpoolctl | 3.5.0 | 3.7.0 |
| typing-extensions | 4.12.1 | 4.16.0 |
| urllib3 | 2.2.1 | 2.8.0 |

---

# Parte 2: upgrade a Django 5.2

Esito: Django **4.2.30 → 5.2.18**. La suite passa **191/191 su Python 3.11 e su Python 3.13**.
Le dipendenze sono state portate a 5.2 con `./upgrade.sh`, dopo aver cambiato i vincoli nel `pyproject.toml`.

## 4. Vincoli del pyproject

### Django 4.2 o 5.2 e pin tolti dalle dipendenze dirette
`pyproject.toml`

<table><tr><th>Prima</th><th>Dopo</th></tr><tr><td>

```python
dependencies = [
    "Django~=4.2.0",
    "django-colorfield==0.10.1",
    "django-tinymce==3.6.1",
    "django-mailer==2.3",
    "django-phonenumber-field[phonenumbers]==6.3.0",
    "requests~=2.0",
    "django-widget-tweaks==1.4.3",
    "beautifulsoup4~=4.6.3",
    "django-formtools==2.2",
    "jinja2<3.1",
    "psycopg[binary]==3.1.19",
    "setuptools>=75.3.2",
    ...
]
requires-python = ">=3.8"
```

</td><td>

```python
dependencies = [
    "Django>=4.2,<5.3",
    "django-colorfield",
    "django-tinymce",
    "django-mailer",
    "django-phonenumber-field[phonenumbers]",
    "requests",
    "django-widget-tweaks",
    "beautifulsoup4",
    "django-formtools",
    "jinja2",
    "psycopg[binary]>=3.1.19",
    "setuptools>=75.3.2,<81",
    ...
]
requires-python = ">=3.10"
```

</td></tr></table>

- `setuptools<81`: da 81 in poi è stato rimosso `pkg_resources`, che usano alcune librerie.
- Python minimo **3.10**: è il minimo di Django 5.2 (Django 4.2 arrivava a 3.8).
- Il gruppo `[dependency-groups] test` (coverage, sphinx, sphinx-rtd-theme) è stato **mantenuto**: la branch `upgrade-django-5.2` lo aveva perso, e sphinx sarebbe uscito dal lock.
- Django è `>=4.2,<5.3`, così il progetto accetta entrambe le versioni:
  - da un clone nuovo, `make run` esegue `migrate.sh`, che pinna le versioni di `pdm.lock` (Django 4.2.13);
  - `make upgrade` toglie quei pin (`upgrade.sh` rimuove `constraint-dependencies` dal pyproject) e arriva a Django 5.2.x.
- Con `Django~=5.2.0` il clone nuovo si bloccava: `migrate.sh` pinnava 4.2.13 e `uv lock` falliva con \"unsatisfiable\".
- Verificato su un clone pulito: `migrate.sh` → Django 4.2.13, 191/191 test OK; `upgrade.sh` → Django 5.2.18 (69 pin rimossi), 191/191 test OK.

## 5. Test: assertEquals rimosso in Python 3.12

### Test: alias deprecato di unittest
`pytition/petition/tests/*.py (11 file, 384 occorrenze)`

<table><tr><th>Prima</th><th>Dopo</th></tr><tr><td>

```python
self.assertEquals(response.status_code, 200)
```

</td><td>

```python
self.assertEqual(response.status_code, 200)
```

</td></tr></table>

Causa: `assertEquals` è un alias deprecato, rimosso in **Python 3.12**. Con la copia di prova, dove uv aveva scelto Python 3.14, davano errore 52 test (tutti con questo messaggio, nessuno legato a Django 5.2). Con `assertEqual` la suite passa anche su 3.13.

## 6. Risultati dei test

| Ambiente | Python | Django | Test |
|---|---|---|---|
| prima di tutto (pin di pdm.lock) | 3.11 | 4.2.13 | 14 errori |
| dopo il primo upgrade e le correzioni | 3.11 | 4.2.30 | 191/191 OK |
| Django 5.2 | 3.11 | 5.2.18 | 191/191 OK |
| Django 5.2 | 3.13 | 5.2.18 | 191/191 OK |

## 7. Versioni cambiate (4.2 → 5.2)

Dove compaiono più versioni separate da `/`, uv ha risolto versioni diverse per Python diversi (il progetto dichiara `>=3.10`).

| Pacchetto | Prima (Django 4.2) | Dopo (Django 5.2) |
|---|---|---|
| alabaster | 0.7.13 / 0.7.16 | 1.0.0 |
| alt-profanity-check | 1.3.2 / 1.6.1 / 1.7.2 / 1.9.1 | 1.7.2 / 1.9.1 |
| asgiref | 3.11.1 / 3.12.1 / 3.8.1 | 3.12.1 |
| backports-zoneinfo | 0.2.1 | - |
| beautifulsoup4 | 4.6.3 | 4.15.0 |
| contourpy | 1.1.1 / 1.3.0 / 1.3.2 / 1.3.3 / 1.4.0 | 1.3.2 / 1.3.3 / 1.4.0 |
| django | 4.2.30 | 5.2.18 |
| django-colorfield | 0.10.1 | 0.14.0 |
| django-formtools | 2.2 | 2.7 |
| django-mailer | 2.3 | 2.3.2 |
| django-phonenumber-field | 6.3.0 | 8.5.0 |
| django-tinymce | 3.6.1 | 5.0.0 |
| django-widget-tweaks | 1.4.3 | 1.5.1 |
| docutils | 0.20.1 / 0.21.2 | 0.21.2 / 0.22.4 |
| fonttools | 4.57.0 / 4.60.2 / 4.65.0 / 4.66.1 | 4.65.0 / 4.66.1 |
| idna | 3.15 / 3.20 | 3.20 |
| imagesize | 1.5.0 / 2.0.1 | 2.0.1 |
| importlib-metadata | 8.5.0 / 8.7.1 | - |
| importlib-resources | 6.4.5 / 6.5.2 | - |
| jinja2 | 3.0.3 | 3.1.6 |
| joblib | 1.4.2 / 1.5.1 / 1.6.0 | 1.5.1 / 1.6.0 |
| kiwisolver | 1.4.7 / 1.5.1 | 1.5.1 |
| markupsafe | 2.1.5 / 3.0.4 | 3.0.4 |
| matplotlib | 3.10.9 / 3.11.2 / 3.7.5 / 3.9.4 | 3.10.9 / 3.11.2 |
| numpy | 1.24.4 / 2.0.2 / 2.2.6 / 2.4.6 / 2.5.3 | 2.2.6 / 2.4.6 / 2.5.3 |
| packaging | 26.2 / 26.3 | 26.3 |
| pillow | 10.4.0 / 11.3.0 / 12.3.0 | 12.3.0 |
| psycopg | 3.1.19 | 3.3.6 |
| psycopg-binary | 3.1.19 | 3.3.6 |
| pygments | 2.19.2 / 2.21.0 | 2.21.0 |
| pyparsing | 3.1.4 / 3.3.3 | 3.3.3 |
| pytz | 2026.5 | - |
| requests | 2.32.4 / 2.32.5 / 2.34.2 | 2.34.2 |
| roman-numerals | - | 4.1.0 |
| scikit-learn | 1.3.2 / 1.6.1 / 1.7.2 / 1.9.1 | 1.7.2 / 1.9.1 |
| scipy | 1.10.1 / 1.13.1 / 1.15.3 / 1.17.1 / 1.18.1 | 1.15.3 / 1.17.1 / 1.18.1 |
| setuptools | 75.3.4 / 82.0.1 / 84.0.0 | 80.10.2 |
| soupsieve | - | 2.10 |
| sphinx | 7.1.2 / 7.3.7 | 8.1.3 / 9.0.4 / 9.1.0 |
| sphinxcontrib-applehelp | 1.0.4 / 2.0.0 | 2.0.0 |
| sphinxcontrib-devhelp | 1.0.2 / 2.0.0 | 2.0.0 |
| sphinxcontrib-htmlhelp | 2.0.1 / 2.1.0 | 2.1.0 |
| sphinxcontrib-qthelp | 1.0.3 / 2.0.0 | 2.0.0 |
| sphinxcontrib-serializinghtml | 1.1.5 / 2.0.0 | 2.0.0 |
| sqlparse | 0.5.5 / 0.6.0 | 0.6.0 |
| threadpoolctl | 3.5.0 / 3.7.0 | 3.7.0 |
| typing-extensions | 4.13.2 / 4.16.0 | 4.16.0 |
| urllib3 | 2.2.3 / 2.6.3 / 2.8.0 | 2.8.0 |
| zipp | 3.20.2 / 3.23.1 | - |

## 8. Branch upgrade-django-5.2

Il lavoro di quella branch (Django 5.2, pin tolti, `requires-python >=3.10`) è ora incluso in questo `pyproject.toml`, quindi la branch è stata cancellata.
Resta un tag di backup, nel caso servano i suoi 13 commit:
```bash
git branch upgrade-django-5.2 backup/upgrade-django-5.2   # per ricrearla
```
Il clone principale `~/Documents/hackathon/framasoft` è stato spostato su `main`.
