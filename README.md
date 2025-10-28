# Django REST API Template

Template starter per progetti Django con REST API, autenticazione JWT, PostgreSQL/PostGIS e gestione media files.

## 🚀 Features

- **Django 5.2+** - Framework web Python moderno
- **Django REST Framework** - API RESTful complete
- **JWT Authentication** - Autenticazione sicura con token
- **PostgreSQL/PostGIS** - Database relazionale con supporto geospaziale
- **Custom User Model** - Modello utente personalizzabile
- **Media Files Management** - Gestione upload e storage file
- **Environment Variables** - Configurazione tramite `.env`
- **Makefile** - Comandi rapidi per development
- **Logging** - Sistema di logging configurato

## 📋 Prerequisiti

- Python 3.12+
- PostgreSQL 14+ (con estensione PostGIS se necessaria)
- uv (Python package manager) - `pip install uv`

## 🛠️ Setup Rapido

### 1. Clona/Usa il Template

```bash
# Se usi GitHub template
gh repo create my-project --template your-username/django-template

# Oppure clona direttamente
git clone <repo-url> my-project
cd my-project
```

### 2. Configura Ambiente

```bash
# Copia il file di esempio
cp .env.example .env

# Modifica .env con le tue configurazioni
nano .env
```

### 3. Setup Database

```bash
# Crea database PostgreSQL
createdb your_db_name

# Se usi PostGIS
psql your_db_name -c "CREATE EXTENSION postgis;"
```

### 4. Installa Dipendenze

```bash
# Con uv (raccomandato)
uv sync

# Oppure con pip
pip install -e .
```

### 5. Inizializza Progetto

```bash
# Applica migrazioni
make migrate

# Crea superuser
make createsu
```

### 6. Avvia Server

```bash
make serve
# Server disponibile su http://0.0.0.0:8000
```

## 📁 Struttura Progetto

```
.
├── backend/               # Configurazione principale Django
│   ├── settings.py        # Settings con env variables
│   ├── urls.py           # URL routing principale
│   └── wsgi.py           # WSGI configuration
├── users/                # App gestione utenti
│   ├── models.py         # Custom User model
│   └── ...
├── photos/               # App esempio (rinomina/rimuovi)
│   ├── models.py         # Models esempio
│   ├── serializers.py    # DRF serializers
│   ├── views.py          # API views
│   └── urls.py           # URL routing app
├── media/                # File caricati dagli utenti
├── manage.py             # Django management
├── Makefile              # Comandi rapidi
├── pyproject.toml        # Dipendenze progetto
└── .env                  # Variabili d'ambiente (non committare!)
```

## ⚙️ Configurazione

### Variabili d'Ambiente (.env)

```env
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_ENGINE=django.contrib.gis.db.backends.postgis
DB_NAME=your_db_name
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432

# Media & Static
MEDIA_ROOT=media
STATIC_ROOT=staticfiles
```

### Comandi Makefile

```bash
make serve          # Avvia development server
make migrate        # Applica migrazioni database
make makemigrations # Crea nuove migrazioni
make createsu       # Crea superuser
```

## 🔐 API Endpoints

### Autenticazione JWT

```
POST /api/token/          # Ottieni token (login)
POST /api/token/refresh/  # Refresh token
POST /api/token/verify/   # Verifica token
```

### Esempio uso JWT

```bash
# Login
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"user","password":"pass"}'

# Risposta: {"access":"...","refresh":"..."}

# Usa access token nelle richieste
curl -H "Authorization: Bearer <access_token>" \
  http://localhost:8000/api/posts/
```

## 🏗️ Personalizzazione Template

### 1. Rinomina Progetto

```bash
# Rinomina cartella principale
mv backend your_project_name

# Aggiorna riferimenti in:
# - manage.py (DJANGO_SETTINGS_MODULE)
# - settings.py (ROOT_URLCONF, WSGI_APPLICATION)
# - wsgi.py e asgi.py
```

### 2. Rimuovi App Esempio

```bash
# Se non ti serve l'app 'photos'
rm -rf photos/

# Rimuovi da settings.py:
# INSTALLED_APPS -= ['photos']

# Rimuovi da urls.py:
# path('api/posts/', include('photos.urls'))
```

### 3. Crea Nuove App

```bash
uv run python manage.py startapp your_app_name

# Aggiungi a INSTALLED_APPS in settings.py
# Crea models, serializers, views, urls
```

## 🗄️ Database

### SQLite (Development)

Modifica `.env`:
```env
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3
```

### PostgreSQL (Production)

```env
DB_ENGINE=django.db.backends.postgresql
DB_NAME=production_db
DB_USER=prod_user
DB_PASSWORD=secure_password
DB_HOST=db.example.com
DB_PORT=5432
```

### PostGIS (Geospatial)

```env
DB_ENGINE=django.contrib.gis.db.backends.postgis
```

Assicurati che l'estensione PostGIS sia installata.

## 📦 Dipendenze Principali

- `django` - Framework web
- `djangorestframework` - REST API
- `djangorestframework-simplejwt` - JWT auth
- `python-decouple` - Environment variables
- `psycopg` - PostgreSQL adapter
- `pillow` - Image processing

## 🚀 Deploy

### Preparazione

```bash
# Raccogli static files
python manage.py collectstatic

# Disabilita DEBUG
DEBUG=False

# Configura ALLOWED_HOSTS
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Usa database production
# Configura SECRET_KEY sicura
```

### Gunicorn (WSGI Server)

```bash
pip install gunicorn
gunicorn backend.wsgi:application --bind 0.0.0.0:8000
```

## 🧪 Testing

```bash
# Run all tests
uv run python manage.py test

# Test specifica app
uv run python manage.py test users

# Con coverage
uv run coverage run manage.py test
uv run coverage report
```

## 📝 Best Practices

1. **Non committare mai `.env`** - Usa `.env.example`
2. **Usa SECRET_KEY diverse** per dev/production
3. **DEBUG=False** in production
4. **Backup database** regolari
5. **Use environment variables** per tutte le config sensibili
6. **Versiona le migrazioni** in git
7. **Documenta le tue API** con DRF spectacular o simili

## 🤝 Contribuire

1. Fork il progetto
2. Crea feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push al branch (`git push origin feature/AmazingFeature`)
5. Apri Pull Request

## 📄 Licenza

MIT License - Vedi LICENSE file per dettagli

## 👤 Autore

Il tuo nome - [@tuoaccount](https://twitter.com/tuoaccount)

## 🙏 Riconoscimenti

- Django Documentation
- Django REST Framework
- Community Django Italia
