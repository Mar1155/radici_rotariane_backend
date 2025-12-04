# =============================================================================
# Django Project Makefile
# =============================================================================
# Quick commands for common Django development tasks
# =============================================================================

.PHONY: help serve migrate makemigrations createsu shell test clean install setup

# Default target
help:
	@echo "Available commands:"
	@echo "  make serve          - Start development server"
	@echo "  make migrate        - Run database migrations"
	@echo "  make makemigrations - Create new migrations"
	@echo "  make createsu       - Create superuser"
	@echo "  make shell          - Open Django shell"
	@echo "  make test           - Run tests"
	@echo "  make test-coverage  - Run tests with coverage report"
	@echo "  make install        - Install dependencies"
	@echo "  make setup          - Initial project setup"
	@echo "  make clean          - Remove Python cache files"
	@echo "  make format         - Format code with black"
	@echo "  make lint           - Check code with flake8"
	@echo "  make collectstatic  - Collect static files"

# Start development server
serve:
	@IP=$$(ifconfig | awk '/inet 192\.168/{print $$2; exit}'); \
	echo "🚀 Starting server..."; \
	echo "📡 Available on:"; \
	echo "   - http://192.168.1.7:8000"; \
	echo "   - http://192.168.1.7:8000"; \
	if [ -n "$$IP" ]; then echo "   - http://$$IP:8000"; fi; \
	echo ""; \
	uv run daphne -b 0.0.0.0 -p 8000 backend.asgi:application

# Database migrations
migrate:
	@echo "📦 Running migrations..."
	@uv run python manage.py migrate

makemigrations:
	@echo "🔨 Creating migrations..."
	@uv run python manage.py makemigrations

# Create superuser
createsu:
	@echo "👤 Creating superuser..."
	@uv run python manage.py createsuperuser

# Open Django shell
shell:
	@echo "🐚 Opening Django shell..."
	@uv run python manage.py shell

# Run tests
test:
	@echo "🧪 Running tests..."
	@uv run python manage.py test

test-coverage:
	@echo "🧪 Running tests with coverage..."
	@uv run coverage run manage.py test
	@uv run coverage report
	@uv run coverage html
	@echo "📊 Coverage report generated in htmlcov/"

# Install dependencies
install:
	@echo "📥 Installing dependencies..."
	@uv sync

# Initial setup
setup:
	@echo "🔧 Running initial setup..."
	@bash setup.sh

# Clean Python cache
clean:
	@echo "🧹 Cleaning cache files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Cache cleaned"

# Code formatting
format:
	@echo "🎨 Formatting code with black..."
	@uv run black .

# Code linting
lint:
	@echo "🔍 Checking code with flake8..."
	@uv run flake8 .

# Collect static files
collectstatic:
	@echo "📁 Collecting static files..."
	@uv run python manage.py collectstatic --noinput

# Show Django version
version:
	@echo "Django version:"
	@uv run python -m django --version
