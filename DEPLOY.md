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

> ⚠️ **Il database di produzione va azzerato, non migrato.** Vale ancora, e
> ora c'e' un motivo in piu': wagtail-localize e' uscito dal progetto, e
> togliere un'app lascia le sue tabelle orfane e `django_migrations` con righe
> che non hanno piu' un'app a cui appartenere.
>
> (motivo originale) Le migrazioni sono
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

### Railway (servizio backend) — tutte in una volta

Non si aggiungono una per una: nella scheda **Variables** del servizio c'e'
**RAW Editor**, che accetta un blocco `.env` incollato.

> ⚠️ Il RAW Editor mostra le variabili **gia' presenti** e salva quello che
> resta nella casella: e' una sostituzione, non un'aggiunta. Apri l'editor,
> **aggiungi** le righe che mancano a quelle che vedi, e non cancellare quelle
> che Railway ha messo da sola (`DATABASE_URL`, `REDIS_URL`, le `RAILWAY_*`).

Questo e' il blocco completo. Le righe `${{...}}` **non** vanno sostituite:
sono riferimenti, e restano allineati se Railway ruota le credenziali.
`NomeDelBucket` e' il nome che hai dato al servizio Storage Bucket.

```sh
# --- Django
SECRET_KEY=GENERA_UN_VALORE
DEBUG=False
ALLOWED_HOSTS=DOMINIO-RAILWAY
CSRF_TRUSTED_ORIGINS=https://DOMINIO-RAILWAY
CORS_ALLOWED_ORIGINS=https://DOMINIO-VERCEL

# --- Indirizzi
WAGTAILADMIN_BASE_URL=https://DOMINIO-RAILWAY
FRONTEND_BASE_URL=https://DOMINIO-VERCEL
REVALIDATE_SECRET=LO_STESSO_CHE_METTI_SU_VERCEL

# --- Traduzione
ANTHROPIC_API_KEY=LA_TUA_CHIAVE
TRANSLATION_MODEL=claude-haiku-4-5-20251001

# --- Media sul bucket Railway
USE_S3=True
AWS_STORAGE_BUCKET_NAME=${{NomeDelBucket.BUCKET}}
AWS_ACCESS_KEY_ID=${{NomeDelBucket.ACCESS_KEY_ID}}
AWS_SECRET_ACCESS_KEY=${{NomeDelBucket.SECRET_ACCESS_KEY}}
AWS_S3_REGION_NAME=${{NomeDelBucket.REGION}}
AWS_S3_ENDPOINT_URL=${{NomeDelBucket.ENDPOINT}}

# --- Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
```

I quattro valori da riempire a mano:

| | come |
|---|---|
| `SECRET_KEY` | `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `REVALIDATE_SECRET` | stesso comando, e **lo stesso valore** anche su Vercel |
| `DOMINIO-RAILWAY` / `DOMINIO-VERCEL` | i due domini, senza `https://` nel solo `ALLOWED_HOSTS` |
| `ANTHROPIC_API_KEY` | dalla console Anthropic |

`DATABASE_URL` e `REDIS_URL` non stanno nel blocco apposta: le collega Railway
da sola quando Postgres e Redis sono nello stesso progetto. Se le riscrivi a
mano, si scollegano.

L'elenco completo, con scritto per ciascuna cosa si rompe se manca, e' in
[.env.example](.env.example).

### Vercel — stessa cosa

Nelle impostazioni del progetto, **Environment Variables**, c'e' un campo che
accetta un `.env` incollato (o il pulsante *Import .env*).

```sh
NEXT_PUBLIC_API_URL=https://DOMINIO-RAILWAY
NEXT_PUBLIC_WS_URL=wss://DOMINIO-RAILWAY
REVALIDATE_SECRET=LO_STESSO_CHE_HAI_MESSO_SU_RAILWAY
```

⚠️ `wss://`, non `https://`, per il secondo: e' l'indirizzo websocket, e con lo
schema sbagliato la chat non si connette e non lo dice.

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
python manage.py migrate          # ~205 migrazioni, qualche minuto
python manage.py build_site       # lingue, pagine, menu, tipi di articolo, geografia, competenze
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

## 8. Le lingue

Il sito ne serve **sei**: italiano, inglese, spagnolo, portoghese, francese,
tedesco. Non sono le lingue piu' parlate al mondo — sono i paesi dove e' andata
la diaspora italiana, cioe' le stesse dei club esteri fra i dati di prova.

Ogni lingua ha **due meta'**, e lo avra' sempre: e' la regola che tiene in piedi
il progetto — l'app la scrive lo sviluppatore, i contenuti l'admin.

| | dove | quando ha effetto |
|---|---|---|
| **contenuti** (pagine, articoli, menu, tag) | una riga in `traduzione.Lingua` | subito: salvarla avvia la traduzione |
| **etichette** (bottoni, form, errori) | `intlayer.config.ts` nel frontend | al deploy successivo |

### Le sei di adesso: cosa resta da fare

I contenuti sono pronti: `seed_lingue` crea tutte e sei, e `translate_pending`
le riempie appena trova la chiave.

Le etichette no: **italiano e inglese sono scritte, le altre quattro no.**
Vanno riempite una volta, dal repository del frontend, con la tua chiave:

```bash
cd radici-rotariane_front-end
export ANTHROPIC_API_KEY=...          # la stessa che hai messo su Railway

npm run i18n:fill                     # senza elenco di lingue: le prende da
                                      # `locales` e in modalita' `complete`
                                      # riempie solo cio' che manca

git diff                              # rileggi: e' l'unico momento in cui una
                                      # persona puo' fermare una traduzione
                                      # sbagliata delle etichette
```

> ⚠️ **Non passare `--output-locales`.** Se lo fai, l'opzione e' *variadica*:
> vuole `es pt fr de` separati da spazi. Scritto con le virgole —
> `--output-locales es,pt,fr,de` — viene letto come **una sola lingua** che si
> chiama cosi', non corrisponde a niente, e il comando stampa `No locales to
> fill, Skipping` per ogni file e **esce con successo**. Sembra che abbia
> funzionato e non ha fatto niente.
>
> Per sapere a che punto sei: `npx intlayer content test` elenca cosa manca,
> lingua per lingua.

⚠️ **Quel rapporto segnala `rotaSpace` come mancante in tutte le lingue,
italiano compreso, anche quando e' completo.** E' un falso positivo: il file ha
103 voci su 103 con le sei lingue, e non c'e' una foglia incompleta ne' nel
dizionario unito ne' in quello non unito. Il via libera non e' "Total missing:
0" ma **"resta solo rotaSpace"**.

La prova vera e' un'altra, e vale la pena farla: metti tutte le lingue in
`requiredLocales` e lancia `npm run build`. Se passa, ogni `t({})` del progetto
ha tutte le lingue — il type-check lo pretende, e non si lascia ingannare.

Poi, in `intlayer.config.ts`, sposta le quattro lingue **anche** in
`requiredLocales`. Da quel momento una chiave nuova senza traduzione rompe la
build invece di ricadere in silenzio sull'italiano — che e' quello che vuoi,
una volta che le traduzioni ci sono.

Infine `git commit && git push`.

### Aggiungerne una domani

```bash
# 1. contenuti: /cms/ -> Struttura -> Lingue -> nuova riga. Basta questo, e il
#    server comincia a riempirla. Il sito continua a funzionare: chi la
#    sceglie legge i contenuti nella sua lingua e i bottoni in italiano.

# 2. etichette, nel frontend:
#    - aggiungi la lingua a `locales` in intlayer.config.ts
npm run i18n:fill                    # riempie cio' che manca, in tutte le lingue
#    - rileggi il diff, spostala in `requiredLocales`, commit
```

> ⚠️ `i18n:fill` **non va nel deploy**: riscrive i file sorgente, quindi in un
> container si perde al riavvio, ogni deploy ripaga il modello, e il testo
> cambierebbe fra un deploy e l'altro senza che nessuno abbia toccato niente.

### Il modello, e quanto costa

`claude-haiku-4-5-20251001`, sia per i contenuti (`TRANSLATION_MODEL`) sia per
le etichette. Haiku e non un modello piu' grande perche' i testi sono brevi, il
glossario e' in prosa nel system prompt, e il compito e' meccanico — mentre il
prezzo si moltiplica per ogni lingua registrata.

Due cose rendono la scelta sicura invece che ottimistica: `MotoreClaude`
**solleva** se il modello non restituisce esattamente le stesse chiavi, quindi
un fraintendimento si vede invece di passare in silenzio; e tutto finisce nella
coda di revisione, dove si corregge per frase. Se la qualita' non bastasse,
`TRANSLATION_MODEL` e' una variabile d'ambiente e si alza senza toccare codice.

⚠️ Se `translate_pending` stampa `Motore: identita`, **fermati**: sta salvando
l'originale al posto della traduzione, e il sito si vedra' in italiano in tutte
le lingue. Le cause sono due — la chiave assente, o il pacchetto `anthropic`
non installato — e `python manage.py check --deploy` le nomina entrambe
(`deploy.W004`, `deploy.W007`). Rimossa la causa basta rilanciare
`translate_pending`: cio' che il motore di identita' aveva scritto si ritraduce
da solo, senza `--forza`.

⚠️ Con sei lingue il **primo** giro di `translate_pending` in produzione fa
circa **3.800 traduzioni** (720 oggetti × 5 lingue di arrivo). E' una spesa una
volta sola: dopo, si traduce solo cio' che cambia. Per farla a scaglioni e
guardare quanto costa prima di lanciarla tutta:

```bash
python manage.py translate_pending --limite 20    # 20 oggetti per modello
python manage.py translate_pending --lingua es    # una lingua alla volta
```

⚠️ Un giro intero dura a lungo, e una sessione che cade lo interrompe. Il
comando e' riprendibile — rilanciato, salta cio' che e' gia' fatto — ma **due
giri insieme traducono le stesse cose e le pagano due volte**, quindi il
secondo si rifiuta di partire finche' il primo e' vivo. Per non dipendere
dalla sessione:

```bash
nohup python manage.py translate_pending > /tmp/traduzioni.log 2>&1 &
tail -f /tmp/traduzioni.log    # si riattacca dopo una disconnessione
```

Il tetto di spesa su console.anthropic.com resta la rete di sicurezza: superato,
l'API risponde 429 e non addebita altro.

## 9. La coda di revisione

Le traduzioni prodotte da una macchina si rivedono da
`/cms/snippets/traduzione/traduzione/`: un campo per frase, con accanto il
testo di partenza. Correggerne una la **blocca**, e da li' in poi la
ritraduzione automatica la lascia stare — per frase, non per articolo, quindi
il resto continua a rinfrescarsi.

## 10. Le traduzioni automatiche — non serve nessun cron

Il server traduce da solo. Un articolo pubblicato, una pagina salvata dal
pannello, un post, un commento, un messaggio: al salvataggio finiscono in coda
e sono tradotti in pochi secondi, senza far aspettare chi ha premuto Pubblica.

**Una alla volta.** La coda ha un solo lavoratore: dieci articoli pubblicati
di fila diventano dieci traduzioni in fila, non dieci chiamate simultanee al
modello — che si prenderebbero un 429 e terrebbero aperte dieci connessioni al
database. Lo stesso oggetto salvato cinque volte si traduce una volta sola, e
con l'ultima versione.

**Un riavvio non perde niente.** La coda vive nella memoria del processo,
quindi un deploy a meta' lavoro la azzera. Per questo, all'avvio, il server
ripassa una volta tutto cio' che non ha ancora tutte le lingue e recupera
quello che mancava. Se le istanze sono piu' d'una, il lucchetto fa in modo che
a ripassare sia una sola.

Quando non c'e' niente di nuovo il ripasso non costa niente: confronta le
impronte dei testi e passa oltre, senza chiamare il modello.

`translate_pending` resta, e serve in due casi: dopo un `build_site` o un
`seed_*`, perche' i comandi di gestione non accendono la coda apposta (creano
centinaia di oggetti in un colpo); e quando si vuole forzare qualcosa a mano.

Per fermare la spesa di colpo: `TRADUZIONE_IN_SOTTOFONDO=false`. Il sito resta
in piedi, i contenuti restano nella lingua in cui sono scritti, e i lettori
vedono la nota che lo dice.

---

## Cosa resta fuori

- **Domini propri**: per ora vanno quelli di Vercel e Railway. Cambiarli
  significa aggiornare le sei variabili che li contengono.
- **Dati veri**: `seed_demo --reset` cancella i dati di prova tenendo i
  superuser, quando sara' il momento.
- **Deploy successivi con migrazioni nuove**: `migrate` va rilanciato a mano
  prima di pubblicare, non parte da solo.


---

## Una nota su `build_site` e le traduzioni

`build_pages_sezioni` e `build_page_home` ricostruiscono il corpo delle pagine
da codice Python, e Wagtail assegna id nuovi ai blocchi a ogni salvataggio. Le
traduzioni sono attaccate a quegli id: **rilanciare `build_site` le invalida**.

Non e' un regresso — prima quelle pagine non erano tradotte affatto — ma e' una
trappola. Dopo ogni `build_site` in produzione:

```bash
python manage.py translate_pending
```

Le pagine costruite da `cms/contenuti/*.json` (`/partner`, `/cip`, `/progetto`,
`/rota-space`, `/skills`, `/rotariani-nel-mondo`) non hanno il problema: gli id
sono versionati nel repository. Portare anche le altre due li' e' lavoro per
un'altra volta.
