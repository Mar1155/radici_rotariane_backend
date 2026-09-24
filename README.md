# Radici Rotariane — Backend

Panoramica rapida della struttura del progetto e dei suoi componenti principali.

## Struttura essenziale

- `backend/` — Configurazione Django (settings, urls, asgi/wsgi) e middleware principali.
- `users/` — App utenti, modelli e logica di autenticazione.
- `chat/` — App realtime/Channels per messaggistica.
- `forum/` — App forum e contenuti.
- `section/` — App articoli (i contenuti scritti da soci e club).
- `cms/` — Wagtail: pagine, menu, tipi di articolo, geografia.
- `traduzione/` — le lingue e **una sola** tabella di traduzione, per qualunque
  contenuto stia nel database: articoli, post, commenti, messaggi, pagine,
  menu, etichette. Cosa si traduce lo dichiara `traducibili.py`.
- `manage.py` — Entry point Django.
- `requirements.txt` — Dipendenze runtime.
- `railpack.json` — Comando di avvio in produzione.
- `.env.example` — Tutte le variabili d'ambiente, con spiegazione.

## Ripartire da zero

```bash
python manage.py migrate
python manage.py build_site     # lingue, pagine, menu, tipi di articolo, geografia
python manage.py seed_demo      # account, articoli, forum, chat
python manage.py translate_pending   # traduzioni (serve ANTHROPIC_API_KEY)
```

## Dati di prova

Popola il database con account, articoli, forum e chat di esempio:

```bash
python manage.py seed_demo            # aggiunge cio' che manca
python manage.py seed_demo --reset    # prima cancella (tiene i superuser)
```

Le credenziali degli account generati sono in [ACCESSI-DEMO.md](ACCESSI-DEMO.md),
insieme all'ordine dei comandi da eseguire su un database vuoto.

## Variabili d'ambiente

L'elenco completo, con spiegazione di cosa succede se una manca, sta in
[.env.example](.env.example). Copialo in `.env` e riempi i valori.

Quel file e' l'unica lista: se ne aggiungi una al codice, aggiungila li'.


## Messa in produzione

### Le migrazioni non partono da sole

`railpack.json` avvia solo `collectstatic` e il server. Le migrazioni si
lanciano a mano, una volta, **prima** del primo deploy:

```bash
python manage.py migrate      # ~220 migrazioni: qualche minuto
python manage.py build_site   # pagine, menu, tipi di articolo, geografia
python manage.py createsuperuser
```

Sono fuori dall'avvio perche' il primo `migrate` dura piu' dell'attesa
concessa al controllo di salute: il servizio verrebbe dichiarato morto e
riavviato a meta' migrazione. E perche' con piu' istanze partirebbero in
parallelo sullo stesso database.

Quando un deploy successivo porta migrazioni nuove, vanno lanciate allo stesso
modo prima di pubblicarlo.

### Cosa serve accanto

| Componente | Perche' | Se manca |
|---|---|---|
| PostgreSQL | Database | non parte |
| Redis | Django Channels | chat e notifiche mute, il resto funziona |
| SMTP | Verifica dell'indirizzo | **nessuno riesce a registrarsi** |
| S3 | File caricati | spariscono a ogni riavvio del container |
| `ANTHROPIC_API_KEY` | Traduzione automatica | i contenuti restano nella lingua d'origine |

Gli statici non vanno su S3: li serve whitenoise dall'immagine, generati da
`collectstatic` a ogni avvio. Su S3 vanno solo i media, cioe' i file caricati
dagli utenti e dal CMS. Per verificare che il bucket sia a posto:

```bash
python manage.py check_s3
```

Scrive un file, lo rilegge, ne scarica l'URL pubblico e lo cancella. Se la
lettura non torna 200 il bucket non e' leggibile dal browser, e nessuna
immagine si vedra' sul sito.

### Le traduzioni vogliono un cron

`translate_pending` traduce cio' che e' stato scritto e non ha ancora tutte le
lingue. Non gira dentro una richiesta: va messo su un'esecuzione periodica,
ogni cinque minuti.

```bash
*/5 * * * * cd /app && python manage.py translate_pending
```

Su Railway e' un servizio cron separato che punta allo stesso repository, con
`python manage.py translate_pending` come comando.

Senza cron il sito funziona: chi pubblica vede il suo testo, gli altri lo
vedono nella lingua d'origine con la nota che lo dice.


## Le lingue

Stanno in una tabella, non nelle impostazioni: si aggiungono da `/cms/` →
Struttura → Lingue, e il contenuto si traduce da solo al primo giro del cron.

Le **etichette dell'app** (bottoni, form, messaggi d'errore) sono un'altra cosa
e stanno in intlayer, nel repository del frontend: una lingua nuova le vuole
riempite con `npm run i18n:fill` e un commit. E' il confine che regge tutto il
progetto — l'app la scrive lo sviluppatore, i contenuti l'admin — e il selettore
mostra solo le lingue che hanno entrambe le meta'.

La procedura completa e' in [DEPLOY.md](DEPLOY.md#8-aggiungere-una-lingua).
