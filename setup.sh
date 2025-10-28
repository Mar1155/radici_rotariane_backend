#!/bin/bash

# =============================================================================
# Django Project Setup Script
# =============================================================================
# This script helps initialize a new Django project from this template
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored messages
print_message() {
    echo -e "${2}${1}${NC}"
}

print_header() {
    echo ""
    print_message "============================================" "$BLUE"
    print_message "$1" "$BLUE"
    print_message "============================================" "$BLUE"
    echo ""
}

print_success() {
    print_message "✓ $1" "$GREEN"
}

print_error() {
    print_message "✗ $1" "$RED"
}

print_warning() {
    print_message "⚠ $1" "$YELLOW"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Main setup function
main() {
    print_header "Django REST API Template Setup"
    
    # Check Python version
    print_message "Checking Python version..." "$BLUE"
    if ! command_exists python3; then
        print_error "Python 3 is not installed. Please install Python 3.12 or higher."
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    print_success "Python $PYTHON_VERSION found"
    
    # Check uv
    print_message "Checking for uv package manager..." "$BLUE"
    if ! command_exists uv; then
        print_warning "uv not found. Installing uv..."
        pip3 install uv
    fi
    print_success "uv is available"
    
    # Create .env file if not exists
    print_header "Environment Configuration"
    if [ ! -f .env ]; then
        print_message "Creating .env file from .env.example..." "$BLUE"
        cp .env.example .env
        print_success ".env file created"
        print_warning "Please edit .env file with your configuration!"
        
        # Generate a random SECRET_KEY
        print_message "Generating SECRET_KEY..." "$BLUE"
        SECRET_KEY=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
        
        # Replace SECRET_KEY in .env
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" .env
        else
            # Linux
            sed -i "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" .env
        fi
        print_success "SECRET_KEY generated and set in .env"
    else
        print_warning ".env file already exists, skipping..."
    fi
    
    # Install dependencies
    print_header "Installing Dependencies"
    print_message "Installing Python packages with uv..." "$BLUE"
    uv sync
    print_success "Dependencies installed"
    
    # Database setup
    print_header "Database Configuration"
    print_message "Make sure your database is created and configured in .env" "$YELLOW"
    read -p "Have you configured your database? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_message "Running migrations..." "$BLUE"
        uv run python manage.py migrate
        print_success "Migrations completed"
        
        # Create superuser
        read -p "Do you want to create a superuser now? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            uv run python manage.py createsuperuser
        fi
    else
        print_warning "Skipping database migrations. Run 'make migrate' when ready."
    fi
    
    # Collect static files (optional)
    print_header "Static Files"
    read -p "Do you want to collect static files? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        uv run python manage.py collectstatic --noinput
        print_success "Static files collected"
    fi
    
    # Final message
    print_header "Setup Complete!"
    print_success "Your Django project is ready!"
    echo ""
    print_message "Next steps:" "$BLUE"
    echo "  1. Review and edit .env file with your configuration"
    echo "  2. Configure your database connection in .env"
    echo "  3. Run migrations: make migrate"
    echo "  4. Create a superuser: make createsu"
    echo "  5. Start the development server: make serve"
    echo ""
    print_message "Useful commands:" "$BLUE"
    echo "  make serve          - Start development server"
    echo "  make migrate        - Run database migrations"
    echo "  make makemigrations - Create new migrations"
    echo "  make createsu       - Create superuser"
    echo "  make test           - Run tests"
    echo ""
    print_message "Documentation: Check README.md for more information" "$GREEN"
    echo ""
}

# Run main function
main
