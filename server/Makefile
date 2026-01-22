export PIPENV_VERBOSITY=-1
OS := $(shell uname -s 2>/dev/null || echo not)

.PHONY: setup
setup:
	make migrate
	make superuser
	make run
	
.PHONY: run
run:
	pipenv run python src/manage.py runserver 0.0.0.0:8001

.PHONY: shell
shell:
	pipenv run python src/manage.py shell


	from django.core.management.utils import get_random_secret_key

.PHONY: superuser
superuser:
	DJANGO_SUPERUSER_PASSWORD=admin pipenv run python src/manage.py createsuperuser --no-input \
		--username admin@admin.com \
		--email admin@admin.com

.PHONY: migrate
migrate:
	pipenv run python src/manage.py makemigrations
	pipenv run python src/manage.py migrate

.PHONY: clean
clean:
	rm -rf ./src/db.sqlite3
	rm -rf ./src/__pycache__
	rm -rf ./src/shyft/__pycache__

.PHONY: collectstatic
collectstatic:
	pipenv run python src/manage.py collectstatic --no-input

.PHONY: run/gunicorn
run/gunicorn:
	PYTHONPATH=src gunicorn the1cfutures.wsgi:application --bind 0.0.0.0:8000

.PHONY: docker/build
docker/build:
	docker build -f ./Dockerfile -t bullbear:latest .

.PHONY: tidy
tidy:
	pipenv run autoflake --in-place --remove-all-unused-imports -r --exclude migrations ./src
	pipenv run isort --atomic ./src/
	pipenv run black ./src/ --exclude=migrations
	make typecheck

.PHONY: load-fixtures
load-fixtures:
	pipenv run python src/manage.py loaddata \
		src/betengine/fixtures/polygon_contract.json

.PHONY: newapp
newapp:
ifndef APP
	$(error Usage: make newapp APP=your_app_name)
endif
	pipenv run python src/manage.py startapp $(APP) src/$(APP)

.PHONY: typecheck
typecheck:
	pipenv run mypy src --ignore-missing-imports --no-warn-unused-ignores