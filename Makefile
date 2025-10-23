serve:
	@IP=$$(ifconfig | awk '/inet 192\.168/{print $$2; exit}'); \
	echo "SERVER RUN OVER IPV4: $$IP"; \
	uv run python manage.py runserver 0.0.0.0:8000

makemigrations:
	@uv run python manage.py makemigrations

migrate:
	@uv run python manage.py migrate

createsu:
	@uv run python manage.py createsuperuser