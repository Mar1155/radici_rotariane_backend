"""Costruisce l'intero sito nel CMS, nell'ordine giusto.

I comandi singoli si aspettano a vicenda: la HomePage e' il genitore delle
altre pagine, ma i suoi riquadri e i menu rimandano a quelle. Su un database
vuoto nessuno dei due puo' partire per primo. Qui la radice si crea vuota,
poi si riempiono le figlie, poi la home, poi i menu.

Da usare dopo un azzeramento:

    python manage.py migrate
    python manage.py build_site
    python manage.py seed_demo
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from cms.bootstrap import assicura_homepage

PASSI = [
    # La geografia PRIMA dei tipi: `seed_article_types` riconosce quali tag
    # sono in realta' luoghi confrontandoli con l'albero geografico, e senza
    # l'albero li tratta come tag normali. E' cosi' che `itinerario` finiva con
    # i tag obbligatori e nessun tag ammesso: impossibile da pubblicare.
    ('seed_geo', 'aree geografiche'),
    ('seed_article_types', 'tipi di articolo'),
    ('build_pages_statiche', 'pagine a contenuto fisso'),
    ('build_pages_sezioni', 'pagine sezione'),
    ('build_page_home', 'homepage'),
    ('seed_menus', 'menu'),
    ('seed_cms_groups', 'gruppi di redazione'),
]


class Command(BaseCommand):
    help = "Crea tutto il contenuto del CMS, nell'ordine corretto."

    @transaction.atomic
    def handle(self, *args, **options):
        assicura_homepage()
        self.stdout.write('  radice del sito')

        for comando, descrizione in PASSI:
            call_command(comando, verbosity=0)
            self.stdout.write(f'  {descrizione}')

        self.stdout.write(self.style.SUCCESS(
            '\nSito costruito. Per i dati di prova: python manage.py seed_demo'))
