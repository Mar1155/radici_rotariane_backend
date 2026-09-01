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

from cms.models import Menu, MenuItem

# (etichetta, percorso, icona, visibilita')
ESPLORA = [
    ('Homepage', '/', 'Compass'),
    ('Chi siamo', '/progetto', 'Info'),
    ('Skills Network', '/skills', 'Users'),
    ('Scambi e Mobilità', '/scopri/scambi-e-mobilita', 'Globe'),
    ('Calendario delle Radici', '/scopri/calendario-delle-radici', 'Calendar'),
    ('Comitati Inter-Paese', '/cip', 'Handshake'),
    ('Storie e Radici', '/scopri/storie-e-radici', 'BookOpen'),
    ('Scopri la Calabria', '/scopri/scopri-la-calabria', 'MapPin'),
    ('Eccellenze Calabresi', '/scopri/eccellenze-calabresi', 'Award'),
    ('Archivio', '/scopri/archivio', 'Bookmark'),
    ('Partner', '/partner', 'Handshake'),
]

SERVIZI = [
    ('Rota-Space', '/rota-space', 'Users', MenuItem.Visibilita.SEMPRE),
    ('Rotariani nel Mondo', '/rotariani-nel-mondo', 'Globe', MenuItem.Visibilita.SEMPRE),
    ('Adotta un Progetto', '/scopri/adotta-un-progetto', 'Heart', MenuItem.Visibilita.SEMPRE),
    ('Accedi', '/login', None, MenuItem.Visibilita.ANONIMI),
]


class Command(BaseCommand):
    help = 'Crea i menu principale, esplora e servizi.'

    @transaction.atomic
    def handle(self, *args, **options):
        locale = Locale.get_default()

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
                                    route=percorso, icon=icona or '', locale=locale)

        servizi = menu('servizi', 'Servizi',
                       'I collegamenti rapidi: barra di navigazione e prima '
                       'colonna del footer.')
        for i, (etichetta, percorso, icona, vis) in enumerate(SERVIZI):
            MenuItem.objects.create(menu=servizi, sort_order=i, label=etichetta,
                                    route=percorso, icon=icona or '',
                                    visibility=vis, locale=locale)

        for m in (esplora, servizi):
            self.stdout.write(f'  {m.key:12} {m.items.count()} voci')
        self.stdout.write(self.style.SUCCESS(
            '\nDue menu, ciascuno definito una volta. Barra di navigazione e '
            'footer usano entrambi gli stessi: rinominare una voce la cambia '
            'in tutti i posti in cui compare.'))
