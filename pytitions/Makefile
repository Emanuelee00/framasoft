migrate:
	docker compose exec web pdm run python pytition/manage.py migrate

makemigrations:
	docker compose exec web pdm run python pytition/manage.py makemigrations

shell:
	docker compose exec web pdm run python pytition/manage.py shell

test:
	docker compose exec web pdm run python pytition/manage.py test

run:
	docker compose up