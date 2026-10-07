run:
	docker compose up

setup: install migrate

migrate:
	docker compose exec web pdm run python pytition/manage.py migrate

makemigrations:
	docker compose exec web pdm run python pytition/manage.py makemigrations

shell:
	docker compose exec web pdm run python pytition/manage.py shell

test:
	docker compose exec web pdm run python pytition/manage.py test

install:
	pip install -r requirements.txt
	pip install -r requirements_dev.txt