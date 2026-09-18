# Accessi di prova

Account creati da `python manage.py seed_demo`. **Password identica per tutti:**

```
demo12345
```

| Ruolo | Email | Chi è |
|---|---|---|
| Socio | `marco_rossi_1@demo.rotary` | Marco Rossi |
| Club | `rotary_club_milano_duomo@demo.rotary` | Rotary Club Milano Duomo |
| Admin | `admin@demo.rotary` | Superuser: vede tutto, `/cms/` e `/admin/` inclusi |
| Redazione | `redazione@demo.rotary` | Il ruolo del cliente su `/cms/`: pagine, immagini e menu, **non** i tipi di articolo |

L'account **Redazione** serve a vedere il pannello come lo vedra' il cliente:
entrando con quello, le voci "Struttura" (tipi di articolo, geografia) e
"Utenti" non compaiono proprio.

Tutti gli altri account generati usano la stessa password. I soci seguono lo
schema `nome_cognome_N@demo.rotary`, i club `rotary_club_citta_nome@demo.rotary`;
l'elenco completo si vede da `/admin/` oppure con:

```bash
python manage.py shell -c "from users.models import User; print(*User.objects.values_list('email', flat=True), sep='\n')"
```

## Cosa c'è dentro

23 club, 60 soci e 40 articoli sparsi per l'Italia, almeno due per ciascuno dei
dodici tipi, più post del forum, commenti e chat.

Gli articoli non sono scritti a mano: si generano **leggendo il tipo di
articolo** — campi attivi, tag ammessi, elementi informativi. Per questo non
possono violare il modello, e se un tipo cambia il seed lo segue.

## Rigenerare

```bash
python manage.py seed_demo            # aggiunge ciò che manca
python manage.py seed_demo --reset    # prima cancella (tiene i superuser)
```

Se il database è vuoto, prima serve il contenuto del sito:

```bash
python manage.py migrate
python manage.py build_site     # pagine, menu, tipi di articolo, geografia
python manage.py seed_demo      # account, articoli, forum, chat
```

`build_site` esiste perché i comandi singoli si aspettano a vicenda: la
HomePage è il genitore delle altre pagine, ma i suoi riquadri e i menu
rimandano a quelle. Su un database vuoto nessuno dei due può partire per primo.

Unica cosa che il reset non riporta indietro: i **loghi dei partner**, che sono
file caricati e non testo. `build_pages_statiche` dice quali mancano; si
ricaricano da `/cms/` con lo stesso titolo e si rilancia.

## Traduzione automatica

Pagine e articoli si traducono con un modello linguistico, guidato dal glossario
in `traduzione/glossario.py` (i nomi dei Club non si traducono, "Azione
internazionale" diventa "International Service", e così via).

Serve una chiave:

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
TRANSLATION_ENGINE=claude      # è già il default
```

**Senza chiave il sito continua a funzionare**: le traduzioni riportano il testo
originale e finiscono nella coda di revisione, con un avviso nei log. Un
articolo leggibile nella lingua sbagliata è meglio di un articolo assente.

```bash
python manage.py translate_pending              # quel che manca
python manage.py translate_pending --forza      # anche quel che c'è già
```

Va su cron, non dentro una richiesta: tradurre un articolo lungo richiede
secondi e nessuno deve aspettarli premendo "Pubblica". Le correzioni fatte a
mano (`human_locked`) non vengono mai sovrascritte.

Chat e forum non passano di qui: restano su DeepL, con la loro configurazione.

## Se il login rifiuta

Il seed segna le email come verificate. Un account creato in altro modo (da
`/admin/`, o con `createsuperuser`) non lo è, e il login risponde 401 anche con
la password giusta: l'account esiste ma non può entrare. Si sblocca così:

```bash
python manage.py shell -c "
from django.utils import timezone
from users.models import User
User.objects.filter(email='TUA@EMAIL').update(email_verified_at=timezone.now())"
```

## Attenzione

Sono credenziali per l'ambiente **locale**. `seed_demo` non va lanciato contro
l'istanza Railway: queste password sono scritte qui, quindi chiunque legga il
repository può usarle. Se un giorno servissero dati di prova su un ambiente
raggiungibile da fuori, vanno generate password diverse e non versionate.
