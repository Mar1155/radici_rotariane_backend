"""Vocabolari condivisi fra backend e frontend.

Sono un **contratto**: i valori (le chiavi, non le etichette) finiscono nel
database e nelle risposte API, e il frontend li usa per decidere cosa
disegnare. Aggiungere una voce e' sicuro; rinominarla o rimuoverla rompe i
contenuti che la usano.

Le etichette sono in italiano perche' e' la lingua sorgente: la traduzione
delle etichette visibili all'utente avviene sui contenuti, non qui.
"""

# --- A chi si mostra un collegamento -----------------------------------------
# Stesso vocabolario per le voci di menu e per i pulsanti dentro le pagine:
# e' la stessa domanda, e tenerne due elenchi li farebbe divergere.
VISIBILITY_CHOICES = [
    ('always', 'Sempre'),
    ('authenticated', 'Solo a chi ha fatto accesso'),
    ('anonymous', 'Solo a chi non ha fatto accesso'),
]

# --- Numeri della fascia statistiche -----------------------------------------
# Le chiavi sono quelle di GET /api/users/stats/: chi compone sceglie quale
# dato mostrare, non il suo valore.
STAT_CHOICES = [
    ('clubs', 'Club'),
    ('rotarians', 'Rotariani'),
    ('countries', 'Paesi'),
    ('projects', 'Progetti'),
]

# --- Campi di un articolo ----------------------------------------------------
# Corrispondono uno a uno ai campi di section.Card che l'autore compila.
FIELD_CHOICES = [
    ('title', 'Titolo'),
    ('subtitle', 'Sottotitolo'),
    ('content', 'Corpo dell\'articolo'),
    ('coverImage', 'Immagine di copertina'),
    ('gallery', 'Galleria'),
    ('tags', 'Tag tematici'),
    ('date', 'Data'),
    ('location', 'Luogo'),
    ('author', 'Autore'),
    ('infoElements', 'Elementi informativi'),
    ('save', 'Salvabile nei preferiti'),
]
FIELD_KEYS = [k for k, _ in FIELD_CHOICES]

# --- Azioni mostrate sulla card ----------------------------------------------
BUTTON_CHOICES = [
    ('leggi-articolo', 'Leggi articolo'),
    ('approfondisci', 'Approfondisci'),
    ('scopri-di-piu', 'Scopri di piu'),
    ('contatta', 'Contatta'),
    ('condividi', 'Condividi'),
    ('salva', 'Salva'),
    ('email', 'Email'),
    ('whatsapp', 'WhatsApp'),
]
BUTTON_KEYS = [k for k, _ in BUTTON_CHOICES]

# --- Chi puo' pubblicare -----------------------------------------------------
ROLE_CHOICES = [
    ('user', 'Socio'),
    ('club', 'Club'),
    ('admin', 'Amministratore'),
]
ROLE_KEYS = [k for k, _ in ROLE_CHOICES]

# --- Icone -------------------------------------------------------------------
# Nomi lucide-react. Il frontend mappa questi nomi ai componenti icona: una
# voce qui che non esiste la' si traduce in un'icona mancante, quindi un test
# tiene allineati i due insiemi.
ICON_CHOICES = [
    (n, n) for n in [
        'Award', 'Bookmark', 'Calendar', 'Clock', 'Compass', 'DollarSign',
        'Flag', 'Globe', 'Heart', 'Mail', 'MapPin', 'Phone', 'Star', 'Tag',
        'Target', 'TrendingUp', 'Users', 'Utensils', 'Camera', 'BookOpen',
        'Handshake', 'Lightbulb', 'Leaf', 'Music', 'Info',
    ]
]
ICON_KEYS = [k for k, _ in ICON_CHOICES]

# --- Layout della lista articoli ---------------------------------------------
LAYOUT_CHOICES = [
    ('grid', 'Griglia'),
    ('calendar', 'Calendario'),
    ('list', 'Elenco'),
]

COLUMN_CHOICES = [(1, '1'), (2, '2'), (3, '3'), (4, '4')]

# --- Blocchi ammessi nel corpo di un articolo --------------------------------
# Sottoinsieme volutamente piccolo: un articolo non e' una landing page.
BODY_BLOCK_CHOICES = [
    ('paragraph', 'Paragrafo'),
    ('heading', 'Titolo di sezione'),
    ('image', 'Immagine'),
    ('gallery', 'Galleria'),
    ('quote', 'Citazione'),
    ('list', 'Elenco'),
    ('embed', 'Video incorporato'),
]
BODY_BLOCK_KEYS = [k for k, _ in BODY_BLOCK_CHOICES]
