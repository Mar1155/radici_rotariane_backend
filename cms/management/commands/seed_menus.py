"""Crea i menu dalla navigazione oggi scritta a mano.

La sorgente sono `Navbar.tsx` (array delle voci + link di primo livello) e
`Footer.tsx` (le stesse voci, riscritte come JSX). Il seed le unifica in due menu:

  servizi  i collegamenti rapidi (barra di navigazione e prima colonna footer)
  esplora  la tendina (barra di navigazione e seconda colonna footer)

Ciascuno e' definito una volta e usato in entrambi i posti: rinominare una voce
la cambia ovunque compaia.

Idempotente.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from wagtail.models import Locale

from cms.models import Menu, MenuItem, StandardPage

# (etichetta, destinazione, icona[, visibilita'])
#
# Una destinazione che inizia con '/' e' una rotta dell'applicazione (pagine
# fisse: autenticazione, profilo, Rota-Space). Le altre sono slug di pagine
# CMS, e il collegamento punta alla PAGINA, non al suo indirizzo: se il cliente
# la rinomina o la sposta, il menu la segue da solo.
ESPLORA = [
    ('Homepage', '/', 'Compass'),
    ('Chi siamo', 'progetto', 'Info'),
    ('Skills Network', '/skills', 'Users'),
    ('Scambi e Mobilità', 'scambi-e-mobilita', 'Globe'),
    ('Calendario delle Radici', 'calendario-delle-radici', 'Calendar'),
    ('Comitati Inter-Paese', 'cip', 'Handshake'),
    ('Storie e Radici', 'storie-e-radici', 'BookOpen'),
    ('Scopri la Calabria', 'scopri-la-calabria', 'MapPin'),
    ('Eccellenze Calabresi', 'eccellenze-calabresi', 'Award'),
    ('Archivio', 'archivio', 'Bookmark'),
    ('Partner', 'partner', 'Handshake'),
]

# Niente voce "Accedi": la barra di navigazione ha gia' il suo pulsante di
# accesso in fondo, e averlo due volte confonde.
SERVIZI = [
    ('Rota-Space', '/rota-space', 'Users', MenuItem.Visibilita.SEMPRE),
    ('Rotariani nel Mondo', '/rotariani-nel-mondo', 'Globe', MenuItem.Visibilita.SEMPRE),
    ('Adotta un Progetto', 'adotta-un-progetto', 'Heart', MenuItem.Visibilita.SEMPRE),
]


class Command(BaseCommand):
    help = 'Crea i menu principale, esplora e servizi.'

    @transaction.atomic
    def handle(self, *args, **options):
        locale = Locale.get_default()

        pagine = {p.slug: p for p in StandardPage.objects.filter(locale=locale)}

        def destinazione(valore):
            """Rotta dell'app se inizia con '/', altrimenti pagina CMS per slug."""
            if valore.startswith('/'):
                return {'route': valore}
            pagina = pagine.get(valore)
            if pagina is None:
                raise ValueError(
                    f'Il menu rimanda alla pagina "{valore}", che non esiste nel '
                    f'CMS. Esegui prima i comandi build_page_*.')
            return {'page': pagina}

        def menu(key, nome, descrizione):
            m, _ = Menu.objects.update_or_create(
                key=key, locale=locale, defaults={'name': nome, 'description': descrizione})
            m.items.all().delete()
            return m

        esplora = menu('esplora', 'Esplora',
                       'La tendina della barra di navigazione. La stessa lista '
                       'compare anche come colonna del footer: e definita qui '
                       'una volta sola.')
        for i, (etichetta, percorso, icona) in enumerate(ESPLORA):
            MenuItem.objects.create(menu=esplora, sort_order=i, label=etichetta,
                                    icon=icona or '', locale=locale,
                                    **destinazione(percorso))

        servizi = menu('servizi', 'Servizi',
                       'I collegamenti rapidi: barra di navigazione e prima '
                       'colonna del footer.')
        for i, (etichetta, percorso, icona, vis) in enumerate(SERVIZI):
            MenuItem.objects.create(menu=servizi, sort_order=i, label=etichetta,
                                    icon=icona or '', visibility=vis, locale=locale,
                                    **destinazione(percorso))

        for m in (esplora, servizi):
            self.stdout.write(f'  {m.key:12} {m.items.count()} voci')
        self.stdout.write(self.style.SUCCESS(
            '\nDue menu, ciascuno definito una volta. Barra di navigazione e '
            'footer usano entrambi gli stessi: rinominare una voce la cambia '
            'in tutti i posti in cui compare.'))
