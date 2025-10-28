# 📋 Template Customization Checklist

Quando usi questo template per un nuovo progetto, segui questa checklist:

## ✅ Setup Iniziale

- [ ] Copia il template nella nuova directory del progetto
- [ ] Inizializza nuovo repository Git (`rm -rf .git && git init`)
- [ ] Copia `.env.example` in `.env`
- [ ] Genera nuova `SECRET_KEY` e aggiorna `.env`
- [ ] Configura database in `.env`
- [ ] Esegui `./setup.sh` oppure `uv sync`

## ✅ Personalizzazione Progetto

- [ ] Rinomina cartella `radarshot_server` con il nome del tuo progetto
- [ ] Aggiorna `manage.py`: cambia `DJANGO_SETTINGS_MODULE`
- [ ] Aggiorna `settings.py`: cambia `ROOT_URLCONF` e `WSGI_APPLICATION`
- [ ] Aggiorna `wsgi.py` e `asgi.py`: cambia `DJANGO_SETTINGS_MODULE`
- [ ] Aggiorna `pyproject.toml`: nome, descrizione progetto
- [ ] Aggiorna `pytest` config in `pyproject.toml`
- [ ] Aggiorna `README.md`: personalizza con info del progetto
- [ ] Aggiorna `LICENSE`: aggiungi il tuo nome

## ✅ Pulizia Template

- [ ] Rimuovi app `photos` se non serve (e aggiorna `settings.py`, `urls.py`)
- [ ] Personalizza app `users` secondo necessità
- [ ] Rimuovi file `TEMPLATE_USAGE.md`, `QUICKSTART.md`, `TODO.md` (questo file)
- [ ] Pulisci `CHANGELOG.md` e inizia da versione 0.1.0 del tuo progetto

## ✅ Database

- [ ] Crea database PostgreSQL (o configura SQLite per dev)
- [ ] Se usi PostGIS: abilita estensione `CREATE EXTENSION postgis;`
- [ ] Esegui migrazioni: `make migrate`
- [ ] Crea superuser: `make createsu`

## ✅ Configurazione GIS (se necessario)

- [ ] Verifica percorsi librerie GEOS e GDAL in `.env`
- [ ] Su macOS: installa con `brew install postgis gdal geos`
- [ ] Su Linux: installa con `apt-get install postgis gdal-bin`
- [ ] Testa import: `python -c "from django.contrib.gis import geos"`

## ✅ Nuove App Django

- [ ] Crea app custom: `python manage.py startapp myapp`
- [ ] Aggiungi a `INSTALLED_APPS` in `settings.py`
- [ ] Crea `models.py`, `serializers.py`, `views.py`, `urls.py`
- [ ] Registra models in `admin.py`
- [ ] Includi URLs in `urls.py` principale
- [ ] Crea migrations: `make makemigrations myapp`
- [ ] Applica migrations: `make migrate`

## ✅ Testing

- [ ] Scrivi test per i tuoi models
- [ ] Scrivi test per le API
- [ ] Esegui test: `make test`
- [ ] Verifica coverage: `make test-coverage`
- [ ] Configura CI/CD per test automatici

## ✅ Documentazione

- [ ] Aggiorna `README.md` con features specifiche
- [ ] Documenta API endpoints
- [ ] Aggiungi esempi di uso API
- [ ] Considera swagger/redoc per documentazione API
- [ ] Aggiorna `CONTRIBUTING.md` se necessario

## ✅ Sicurezza

- [ ] Genera SECRET_KEY unica per production
- [ ] Configura `DEBUG=False` in production
- [ ] Configura `ALLOWED_HOSTS` correttamente
- [ ] Non committare mai file `.env`
- [ ] Usa HTTPS in production
- [ ] Configura CORS se necessario
- [ ] Review password validators in `settings.py`

## ✅ Performance

- [ ] Configura Redis per caching (opzionale)
- [ ] Setup Celery per task asincroni (opzionale)
- [ ] Configura logging in production
- [ ] Ottimizza query database
- [ ] Setup CDN per static files (opzionale)

## ✅ Deployment Preparation

- [ ] Raccogli static files: `make collectstatic`
- [ ] Test con `DEBUG=False` localmente
- [ ] Configura database production
- [ ] Setup backup database
- [ ] Configura WSGI server (Gunicorn/uWSGI)
- [ ] Configura reverse proxy (Nginx/Apache)
- [ ] Setup monitoring e error tracking
- [ ] Configura email backend per errori

## ✅ Docker (opzionale)

- [ ] Testa build: `docker build -t myproject .`
- [ ] Testa docker-compose: `docker-compose up`
- [ ] Configura volumi per persistenza
- [ ] Setup per production con docker-compose

## ✅ Git e Versioning

- [ ] Primo commit: `git add . && git commit -m "Initial commit"`
- [ ] Crea repository remoto (GitHub/GitLab)
- [ ] Aggiungi remote: `git remote add origin <url>`
- [ ] Push: `git push -u origin main`
- [ ] Setup branch protection rules
- [ ] Configura CI/CD pipeline

## ✅ Post-Deployment

- [ ] Verifica che il sito sia raggiungibile
- [ ] Test login admin: `/admin/`
- [ ] Test API endpoints
- [ ] Verifica upload media files
- [ ] Monitor logs per errori
- [ ] Setup backup automatici
- [ ] Configura SSL certificate
- [ ] Test performance

## 📝 Note Aggiuntive

Aggiungi qui note specifiche per il tuo progetto:

---

Ultima revisione: __________
Progetto: __________
Developer: __________
