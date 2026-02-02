# Radici Rotariane — Backend

Panoramica rapida della struttura del progetto e dei suoi componenti principali.

## Struttura essenziale

- `backend/` — Configurazione Django (settings, urls, asgi/wsgi) e middleware principali.
- `users/` — App utenti, modelli e logica di autenticazione.
- `chat/` — App realtime/Channels per messaggistica.
- `forum/` — App forum e contenuti.
- `section/` — App per sezioni/moduli del progetto.
- `scripts/` — Utility per dati demo.
- `manage.py` — Entry point Django.
- `requirements.txt` — Dipendenze runtime.
- `nixpacks.toml` — Build/deploy Railway (venv + pip).

## Script demo

Popola il database con dati di esempio:

```bash
python scripts/populate_demo.py
```

Opzioni:

```bash
python scripts/populate_demo.py clubs
python scripts/populate_demo.py skills
```

