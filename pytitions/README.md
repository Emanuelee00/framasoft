[![Build Status](http://jenkins.sionneau.net:8080/buildStatus/icon?job=Pytition/master)](http://jenkins.sionneau.net:8080/job/Pytition/job/master/) [![Coverage status](https://img.shields.io/jenkins/coverage/cobertura/http/jenkins.sionneau.net:8080/job/Pytition/job/master.svg)](http://jenkins.sionneau.net:8080/job/Pytition/job/master/lastBuild/cobertura/) [![Documentation Status](https://readthedocs.org/projects/pytition/badge/?version=latest)](https://pytition.readthedocs.io/en/latest/?badge=latest)

# Pytition

## Why using Pytition?

* Because it allows you to host petitions without compromising the privacy of your signatories.
* No tracking, ever: CSS, JS and all resources are self-hosted. Pytition does not use CDN.
* Nice UI: Bootstrap 4 + JQuery 3.
* Based on solid backend technology: Django.
* Responsive UI: works well on phones/tablets/laptops/desktops.
* If you host an instance of Pytition, you can guarantee your signatories that their informations won't leak to third parties.
* It is Open Source and Free Software.

## Features

* [x] Multi-lingual UI with i18n: English, French, Italian, Occitan, Spanish.
* [x] You can pre-visualize petitions before publishing them.
* [x] Easy to use: petition content is typed-in via TinyMCE editors (like WordPress).
* [x] You can setup real SMTP account for the confirmation e-mail so that it is less likely considered as SPAM.
* [x] Supports Open Graph tags to provide description and image to allow nice cards to be shown when people post the petition link on social networks.
* [x] You can propose your signatories to subscribe to a newsletter/mailinglist (via HTTP GET/POST or EMAIL methods).
* [x] You can export signatures in CSV format.
* [x] Support for several organizations on the same Pytition instance [v2.0](https://github.com/pytition/Pytition/milestone/2)
  * Fine grain per-user per-organization permissions
* [x] Email retry support through the use of a mail queue middleware
* [x] Nice (multiple) permlink support for each petition
* [x] Optional share buttons

## Future features

* [ ] Support for multi-lingual petition content: [v3.0](https://github.com/pytition/Pytition/milestone/3)
* [ ] Support for adding several petition templates: [v4.0](https://github.com/pytition/Pytition/milestone/4)
* [ ] Add optional Diaspora share icon

## Install development environment

See [dev/CONTRIBUTE.md](dev/CONTRIBUTE.md)

### Running it locally with `make`

Dependencies are managed with [uv](https://docs.astral.sh/uv/) (`pyproject.toml` + `uv.lock`).
There are two ways to run the project:

* **Without upgrading** (default): the first `make run` installs the **exact versions of `pdm.lock`** (Django 4.2.13 and so on).
* **Upgraded**: `make upgrade` moves everything to the latest compatible versions (Django 5.2.x).

Run these from the `pytitions/` folder:

| Command | What it does |
|---|---|
| `make run` | Starts the PostgreSQL container and the Django dev server on http://127.0.0.1:8000. The first time it also does the initial setup, with the exact `pdm.lock` versions. |
| `make migrate` | Applies new database migrations. **Run it after every `git pull` or upgrade** that adds a migration: `make run` does not do it by itself. |
| `make upgrade` | Upgrades all dependencies to the latest compatible versions (Django 5.2.x). Asks for confirmation first, removes the exact `pdm.lock` pins from `pyproject.toml` and appends only the changed packages to [`upgraded.md`](upgraded.md). |

Notes:

* The first-time setup runs only once: the file `.make-install-stamp` marks it as done
  (it is not committed to git, so every new clone does it again). `make migrate` does
  not create or change that file.
* Before `make upgrade`, commit `uv.lock` and `pyproject.toml`: that is what lets you go back. The command
  prints the exact rollback line, and the same line is saved in `upgraded.md`:
  `git checkout <commit> -- uv.lock pyproject.toml && uv sync --all-groups --no-install-package uwsgi`.
* After an upgrade, run the tests: `cd pytition && python manage.py test`.
* `fixed.md` lists the fixes made for the Django 5.2 upgrade, with before/after code.

## Load testing (`gatling-tests/`)


`gatling-tests/` is a git **submodule**, not a regular folder — cloning this
repo normally leaves it empty. To get its contents:

```bash
git clone --recurse-submodules <this-repo-url>
# or, if you already cloned without that flag:
git submodule update --init
```

## Documentation (Installing in production, configuration, update etc)

See https://pytition.readthedocs.io

## Included dependencies

Those are external projects that are needed and used by Pytition, but included in Pytition source tree:

* Bootstrap 4.2.1
* JQuery 3.3.1
* Popper 1.14.6
* Open Iconic 1.1.1
* TinyMCE 4.9.2
* jQuery Smart Wizard 4

## Dependencies

* Python 3.10 or newer (tested on 3.11 and 3.13)
* Django 4.2.x (default, pinned by `pdm.lock`) or 5.2.x (after `make upgrade`)
* django-tinymce 3.5.0
* django-colorfield 0.8.0
* requests 2.20.x
* beautifulsoup4 4.6.3
* django-formtools 2.2
* bcrypt

## Translations

| Language      | Translation % |
| ------------- | ------------- |
| English       | <a href="https://weblate.framasoft.org/engage/pytition/en/?utm_source=widget"><img src="https://weblate.framasoft.org/widgets/pytition/en/pytitions/svg-badge.svg" alt="État de la traduction" /></a>|
| French  | <a href="https://weblate.framasoft.org/engage/pytition/fr_FR/?utm_source=widget"><img src="https://weblate.framasoft.org/widgets/pytition/fr_FR/pytitions/svg-badge.svg" alt="État de la traduction" /></a>|
| Italian       | <a href="https://weblate.framasoft.org/engage/pytition/it/?utm_source=widget"><img src="https://weblate.framasoft.org/widgets/pytition/it/pytitions/svg-badge.svg" alt="État de la traduction" /></a>|
| Occitan       | <a href="https://weblate.framasoft.org/engage/pytition/oc/?utm_source=widget"><img src="https://weblate.framasoft.org/widgets/pytition/oc/pytitions/svg-badge.svg" alt="État de la traduction" /></a> |
| Spanish       | <a href="https://weblate.framasoft.org/engage/pytition/es/?utm_source=widget"><img src="https://weblate.framasoft.org/widgets/pytition/es/pytitions/svg-badge.svg" alt="État de la traduction" /></a> |
