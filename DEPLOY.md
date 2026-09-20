# Deploy in produzione

Situazione: backend su **Railway**, frontend su **Vercel**, entrambi collegati
ai repository dell'account `rotarianiapp`. Ogni repository locale ha due
remoti — `origin` e' quello di sviluppo, l'altro e' quello da cui parte il
deploy:

| | sviluppo (`origin`) | deploy |
|---|---|---|
| backend | `Mar1155/radici_rotariane_backend` | `back` → `rotarianiapp/radici_rotariane_back` |
| frontend | `upiparillu/radici-rotariane_front-end` | `front` → `rotarianiapp/radici_rotariane_front` |

**Il push su `main` dei repository di deploy fa partire la pubblicazione da
solo**, su entrambi gli hosting. Verificato: l'ultimo deploy e' nato due
secondi dopo il push. Quindi il push e' l'ultimo passo, non il primo.

> ⚠️ **Il database di produzione va azzerato, non migrato.** Le migrazioni sono
> state compattate: la storia registrata nel database attuale non esiste piu' e
> `migrate` fallirebbe. E' il passo 4.

---

## 1. Metti i tetti di spesa (prima di tutto)

Due servizi si pagano a consumo. I tetti vanno messi ora, non dopo.

**Railway** — Workspace → Usage → *Set Usage Limits*. Imposta un **hard limit**
(minimo 10 $; con il piano da 20 $ un tetto a 25-30 $ ha senso). Al
raggiungimento Railway spegne i servizi invece di continuare ad addebitare.
Arrivano avvisi al 75%, 90% e 100%.

**Anthropic** — Console → Settings → Plans & Billing → *Spending Limits*.
Imposta un tetto mensile per l'organizzazione; superato, l'API risponde 429 e
non addebita altro. Per una dimostrazione 5-10 $ al mese sono abbondanti.

Nel codice ci sono gia' dei freni, che valgono per persona e per ora
(`THROTTLE_*` in `.env` se vanno stretti):

| | tetto | perche' |
|---|---|---|
| scrittura articoli, post, commenti, messaggi | 120/ora | ognuno fa partire una traduzione a pagamento |
| caricamento immagini | 60/ora | ognuna occupa spazio sul bucket |
| richieste da autenticati | 2000/ora | |
| richieste anonime | 300/ora | |

Le immagini sono rifiutate sopra i **12 MB** o gli **80 milioni di pixel**,
prima di essere aperte.

---

## 2. Crea il bucket su Railway

Nel progetto Railway: **+ New → Storage Bucket**. Sono bucket S3-compatibili,
0,015 $ per GB al mese, traffico in uscita e operazioni gratuiti — per questa
dimostrazione, pochi centesimi.

Railway espone le credenziali come variabili del bucket: `BUCKET`,
`ACCESS_KEY_ID`, `SECRET_ACCESS_KEY`, `REGION`, `ENDPOINT`.

Sono bucket **privati**: non esistono URL pubblici, i file si servono con un
URL firmato. Il backend lo fa da solo quando trova `AWS_S3_ENDPOINT_URL`.

---

## 3. Variabili d'ambiente

### Railway (servizio backend)

Riferisci le variabili del bucket invece di copiarle, cosi' restano allineate
se Railway le ruota (`NomeDelBucket` e' il nome del servizio bucket):

```
USE_S3=True
AWS_STORAGE_BUCKET_NAME=${{NomeDelBucket.BUCKET}}
AWS_ACCESS_KEY_ID=${{NomeDelBucket.ACCESS_KEY_ID}}
AWS_SECRET_ACCESS_KEY=${{NomeDelBucket.SECRET_ACCESS_KEY}}
AWS_S3_REGION_NAME=${{NomeDelBucket.REGION}}
AWS_S3_ENDPOINT_URL=${{NomeDelBucket.ENDPOINT}}
```

E le altre:

```
SECRET_KEY=            # python -c "import secrets; print(secrets.token_urlsafe(64))"
DEBUG=False
ALLOWED_HOSTS=<dominio-railway>            # senza https://
CSRF_TRUSTED_ORIGINS=https://<dominio-railway>
CORS_ALLOWED_ORIGINS=https://<dominio-vercel>
WAGTAILADMIN_BASE_URL=https://<dominio-railway>
FRONTEND_BASE_URL=https://<dominio-vercel>
REVALIDATE_SECRET=                          # stesso valore su Vercel
ANTHROPIC_API_KEY=
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
```

`DATABASE_URL` e `REDIS_URL` le collega Railway da sole se i servizi Postgres
e Redis sono nello stesso progetto.

L'elenco completo con la spiegazione di cosa si rompe se una manca sta in
[.env.example](.env.example).

### Vercel

```
NEXT_PUBLIC_API_URL=https://<dominio-railway>
NEXT_PUBLIC_WS_URL=wss://<dominio-railway>
REVALIDATE_SECRET=                          # identico a quello su Railway
```

### Email — da verificare

Railway non offre un server SMTP: le variabili devono puntare a un servizio
esterno. Guarda se sul servizio backend esistono gia' `EMAIL_HOST_USER` e
`EMAIL_HOST_PASSWORD`. Se ci sono, va bene cosi'. Se non ci sono, servono: con
Gmail si genera una *password per le app* (non quella dell'account), con Resend
o SendGrid cambiano solo `EMAIL_HOST` e `EMAIL_PORT`.

Senza SMTP la registrazione riesce ma il codice di verifica non arriva mai, e
nessun utente nuovo entra. Per la sola dimostrazione si puo' aggirare con
`AUTO_VERIFY_EMAIL_ON_REGISTER=True` su Railway e
`NEXT_PUBLIC_AUTO_VERIFY_EMAIL=true` su Vercel — ma e' un tappo, non una
soluzione: va tolto prima di aprire al pubblico.

---

## 4. Azzera il database

Dal servizio Postgres su Railway, nella console:

```sql
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
```

In alternativa: cancella il servizio Postgres e creane uno nuovo (cambia
`DATABASE_URL`, che Railway ricollega da sola).

---

## 5. Unisci e pubblica

```bash
# backend
cd radici_rotariane_backend
git checkout main && git merge feat/cms-generalizzazione
git push origin main && git push back main      # <- il push su back pubblica

# frontend
cd ../radici-rotariane_front-end
git checkout main && git merge feat/cms-generalizzazione
git pull front main                             # front/main ha un commit in piu'
git push origin main && git push front main     # <- il push su front pubblica
```

> `front/main` ha un commit che in locale non c'e' (`Update README.md`): senza
> il `pull` il push viene rifiutato.

---

## 6. Dopo il deploy, tre comandi a mano

Dalla shell del servizio backend su Railway:

```bash
python manage.py migrate          # ~220 migrazioni, qualche minuto
python manage.py build_site       # pagine, menu, tipi di articolo, geografia
python manage.py seed_demo        # 23 club, 62 soci, 102 articoli, 20 discussioni
python manage.py createsuperuser  # il tuo accesso a /cms/
```

Non sono nell'avvio automatico apposta: il primo `migrate` dura piu' dell'attesa
concessa al controllo di salute, e il servizio verrebbe ucciso a meta'.

Le credenziali degli account di prova sono in
[ACCESSI-DEMO.md](ACCESSI-DEMO.md).

---

## 7. Verifica

```bash
python manage.py check --deploy   # elenca cosa manca ancora
python manage.py check_s3         # scrive sul bucket, rilegge, scarica, pulisce
```

Poi a mano:

- apri il sito: la homepage e le pagine (`/partner`, `/progetto`, `/cip`, le
  sette sezioni) devono rispondere e mostrare le immagini
- entra su `/cms/` col superuser — se dice "CSRF verification failed" manca
  `CSRF_TRUSTED_ORIGINS`
- accedi con un account di prova e apri una chat
- cambia lingua: i contenuti devono comparire tradotti entro pochi minuti

---

## 8. Il cron delle traduzioni

Su Railway, **+ New → Cron Job** sullo stesso repository, comando
`python manage.py translate_pending`, ogni 5 minuti (`*/5 * * * *`).

Senza, il sito funziona: chi scrive vede il suo testo, gli altri lo vedono
nella lingua d'origine con la nota che lo dice.

---

## Cosa resta fuori

- **Domini propri**: per ora vanno quelli di Vercel e Railway. Cambiarli
  significa aggiornare le sei variabili che li contengono.
- **Dati veri**: `seed_demo --reset` cancella i dati di prova tenendo i
  superuser, quando sara' il momento.
- **Deploy successivi con migrazioni nuove**: `migrate` va rilanciato a mano
  prima di pubblicare, non parte da solo.
