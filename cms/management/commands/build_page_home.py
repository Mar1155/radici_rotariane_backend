"""Costruisce la homepage nel CMS.

E' l'ultima pagina a passare, e l'unica che va **sostituita** invece che
cancellata: Next risolve i segmenti statici prima dei catch-all, ma `/` non e'
un segmento — nessun catch-all lo intercetta. Percio' `app/page.tsx` resta, e
diventa un guscio che legge dal CMS come fa `app/[...slug]/page.tsx`.

Cio' che prima era scritto nel JSX (i tre riquadri di accesso rapido, i quattro
passi per iscriversi, i dieci riquadri di sezione con i colori copiati dai
metadati) diventa contenuto: il cliente lo riordina, lo rinomina e lo cambia
da solo.

Idempotente.
"""

import copy

from django.core.management.base import BaseCommand
from django.db import transaction
from wagtail.models import Locale, Page

from cms.bootstrap import assicura_homepage
from cms.models import StandardPage


def pagina(slug):
    """Segnaposto risolto in fase di costruzione: qui non c'e' ancora il DB."""
    return ('__pagina__', slug)


ACCESSO_RAPIDO = [
    ('MessageCircle', 'Rota-Space',
     'Spazio virtuale per chat, videoconferenze e collaborazioni',
     'Entra nello Space', '/rota-space'),
    ('Heart', 'Adotta un Progetto',
     'Scopri i progetti dei Club Rotary italiani',
     'Scopri i progetti', pagina('adotta-un-progetto')),
    ('Globe', 'Rotariani nel Mondo',
     'Esplora la mappa dei club registrati su Radici Rotariani nel Mondo',
     'Esplora la mappa', '/rotariani-nel-mondo'),
]

PASSI = [
    ('Registrati', 'Usa la tua email e il tuo ID MyRotary per registrarti'),
    ('Accetta', 'Regolamento e privacy policy'),
    ('Personalizza', 'Il tuo profilo con Club, interessi e competenze'),
    ('Connettiti', 'Inizia a scoprire e collaborare'),
]

# (icona, etichetta, accento, destinazione)
RIQUADRI = [
    ('BookOpen', 'Storie e Radici', 'sky', pagina('storie-e-radici')),
    ('MapPin', "Scopri l'Italia", 'teal', pagina('scopri-l-italia')),
    ('Award', 'Eccellenze Italiane', 'emerald', pagina('eccellenze-italiane')),
    ('Users', 'Scambi e Mobilità', 'rose', pagina('scambi-e-mobilita')),
    ('Bookmark', 'Archivio', 'slate', pagina('archivio')),
    ('Briefcase', 'Skills Network', 'brand-secondary', '/skills'),
    ('Calendar', 'Calendario ed Eventi', 'amber', pagina('calendario-delle-radici')),
    ('Heart', 'Chi siamo', 'stone', pagina('progetto')),
    ('Globe', 'Comitati Inter-Paese', 'brand-primary', pagina('cip')),
    ('Handshake', 'Partner e Sponsor', 'brand-secondary', pagina('partner')),
]

NUMERI = [
    ('clubs', 'Club Italiani', '50+'),
    ('rotarians', 'Rotariani Connessi', '1000+'),
    ('countries', 'Paesi Coinvolti', '25+'),
    ('projects', 'Progetti Attivi', '100+'),
]


class Command(BaseCommand):
    help = 'Crea (o aggiorna) la homepage.'

    @transaction.atomic
    def handle(self, *args, **options):
        locale = Locale.get_default()
        home = assicura_homepage()

        pagine = {p.slug: p for p in StandardPage.objects.filter(locale=locale)}

        def link(etichetta, destinazione, visibilita='always'):
            """Un collegamento: a una pagina del CMS o a una rotta dell'app."""
            base = {'label': etichetta, 'page': None, 'route': '', 'external_url': '',
                    'visibility': visibilita}
            if isinstance(destinazione, tuple):
                slug = destinazione[1]
                if slug not in pagine:
                    raise ValueError(
                        f'La homepage rimanda alla pagina "{slug}", che non esiste '
                        f'nel CMS. Esegui prima gli altri comandi build_page_*.')
                base['page'] = pagine[slug]
            else:
                base['route'] = destinazione
            return base

        corpo = [
            ('split_hero', {
                'pill': 'Distretto Rotary 2102',
                'title_top': 'Radici Rotariane',
                'title_highlight': 'nel Mondo',
                'subtitle': 'Il ponte digitale tra identità, memoria e futuro',
                'note_title': 'Benvenuti su Radici Rotariane nel Mondo',
                'note_body': (
                    "La piattaforma digitale nata nel Distretto Rotary 2102 e aperta a "
                    "tutta Italia, per valorizzare le radici italiane dei rotariani "
                    "all'estero e promuovere l'Azione internazionale. Qui puoi "
                    "connetterti, creare nuove collaborazioni, avviare nuovi gemellaggi "
                    "tra Club e riscoprire i territori da cui parte la tua storia.\n\n"
                    'Accedi con la tua email MyRotary e inizia il viaggio!'),
                # "Registrati" non si mostra a chi ha gia' un account: prima la
                # regola stava nel JSX, ora viaggia col collegamento.
                'primary_cta': link('Registrati Ora', '/register', 'anonymous'),
                'secondary_cta': link('Scopri di più', pagina('progetto')),
                'video_url': '',
                'video_title': 'Video Introduttivo',
                'video_subtitle': "Scopri l'Italia e il Rotary",
            }),
            ('icon_card_grid', {
                'title': 'Accesso Rapido',
                'subtitle': 'Esplora le aree principali della piattaforma',
                'columns': '3', 'surface': 'white',
                'items': [
                    {'icon': icona, 'title': titolo, 'description': descrizione,
                     'accent': 'brand-primary', 'cta': link(etichetta, destinazione)}
                    for icona, titolo, descrizione, etichetta, destinazione in ACCESSO_RAPIDO
                ],
            }),
            ('numbered_steps', {
                'title': 'Come entrare nella community',
                'subtitle': 'Scopri tutte le funzionalità della piattaforma',
                'surface': 'light',
                'steps': [{'title': t, 'description': d} for t, d in PASSI],
                'cta': link('Registrati ora', '/register', 'anonymous'),
            }),
            ('section_tiles', {
                'title': 'Esplora le Sezioni',
                'subtitle': 'Scopri tutte le aree della nostra comunità',
                'columns': '4', 'surface': 'white',
                'tiles': [
                    {'icon': icona, 'label': etichetta, 'accent': accento,
                     'link': link(etichetta, destinazione)}
                    for icona, etichetta, accento, destinazione in RIQUADRI
                ],
            }),
            ('stats_bar', {
                'surface': 'brand-primary',
                'items': [{'source': s, 'label': l, 'fallback': f} for s, l, f in NUMERI],
            }),
            ('cta_banner', {
                'title': 'Pronto a riscoprire le tue radici?',
                'description': (
                    'Unisciti alla community globale dei rotariani di origine italiana '
                    'e inizia a costruire ponti tra culture, progetti e amicizie che '
                    'durano una vita.'),
                'surface': 'brand-secondary',
                'primary_cta': link('Registrati con MyRotary', '/register', 'anonymous'),
                'secondary_cta': link('Scopri di Più', pagina('progetto')),
            }),
        ]

        home.title = 'Radici Rotariane'
        home.body = copy.deepcopy(corpo)
        home.save()
        home.save_revision().publish()
        self.stdout.write(self.style.SUCCESS(
            f'Homepage pubblicata con {len(corpo)} blocchi.'))
