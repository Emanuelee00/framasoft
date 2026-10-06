# Correzioni

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
