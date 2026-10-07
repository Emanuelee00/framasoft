
create-venv: 
	python3 -m venv .venv
# source .venv/bin/activate

install:
	pip install -r requirements.txt
	pip install -r requirements_dev.txt

run:
	docker compose up

migrate:
	docker compose exec web pdm run python pytition/manage.py migrate

populate_db_sample:
	docker compose exec web pdm run python pytition/manage.py gen_orga RAP Greenpeace Attac
	docker compose exec web pdm run python pytition/manage.py gen_user john john --first-name John --last-name Smith
	docker compose exec web pdm run python pytition/manage.py join_org john RAP 
	docker compose exec web pdm run python pytition/manage.py gen_pet -n 10 --orga RAP