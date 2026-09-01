"""Costruisce la pagina /partner nel CMS a partire dai testi attuali.

Non e' una migrazione: e' la ricostruzione della pagina con i blocchi, cosi'
com'e' oggi, per poter poi cancellare il file JSX. Dopo questo passaggio la
pagina si modifica da /cms/ e i testi non stanno piu' in
app/partner/partner.content.ts.

I loghi vengono importati nella libreria immagini di Wagtail: da li' in avanti
si caricano dall'admin, non copiando file in public/.

Idempotente.
"""

import json
from pathlib import Path

from django.core.files.images import ImageFile
from django.core.management.base import BaseCommand
from django.db import transaction
from wagtail.models import Locale, Page

from cms.models import CMSImage, HomePage, StandardPage


class Command(BaseCommand):
    help = 'Crea (o aggiorna) la pagina /partner con i blocchi.'

    def add_arguments(self, parser):
        parser.add_argument('--content', required=True,
                            help='JSON prodotto da scripts/dump-page-content.mjs')
        parser.add_argument('--assets', required=True,
                            help='Cartella public/ del frontend, per i loghi')

    def _immagine(self, cartella: Path, percorso_web: str, titolo: str):
        """Importa un file di public/ nella libreria immagini, una volta sola."""
        # Alcuni partner usano un'emoji invece di un logo: non e' un file.
        if not percorso_web or not percorso_web.startswith('/'):
            return None
        file = cartella / percorso_web.lstrip('/')
        if not file.exists():
            self.stderr.write(f'  ! logo mancante: {file}')
            return None
        esistente = CMSImage.objects.filter(title=titolo).first()
        if esistente:
            return esistente
        with file.open('rb') as fh:
            img = CMSImage(title=titolo)
            img.file.save(file.name, ImageFile(fh), save=True)
        return img

    def _griglia(self, voci, cartella, titolo, descrizione, colonne, sfondo):
        elementi = []
        for v in voci:
            img = self._immagine(cartella, v.get('icon', ''), v.get('name', 'partner'))
            # ListBlock vuole i valori diretti: la forma (tipo, valore) e' degli
            # StreamBlock, dove il tipo dice quale blocco e'.
            elementi.append({
                'name': v.get('name', ''),
                'description': v.get('description', '') or '',
                'logo': img,
                'emoji': '' if img else (v.get('icon', '') or '')[:8],
                'link': v.get('link', '') or '',
                'logo_scale': 100,
            })
        return ('partner_grid', {
            'title': titolo, 'description': descrizione or '',
            'columns': colonne, 'surface': sfondo, 'items': elementi,
        })

    @transaction.atomic
    def handle(self, *args, **options):
        dati = json.loads(Path(options['content']).read_text(encoding='utf-8'))
        cartella = Path(options['assets'])
        locale = Locale.get_default()
        home = HomePage.objects.filter(locale=locale).first()
        if not home:
            self.stderr.write('Nessuna home page: esegui prima la creazione del sito.')
            return

        hero = dati['hero']
        main = dati['mainSponsors']
        ist = dati['institutionalPartners']
        cta = dati['cta']

        corpo = [
            ('hero', {
                'title': hero['title'], 'description': hero['description'],
                'tag': hero.get('tag', ''), 'surface': 'brand-gradient',
                'scroll_to_id': 'main-sponsors',
            }),
            self._griglia(main['sponsors'], cartella, main['title'],
                          main.get('description'), '4', 'white'),
            self._griglia(ist['partners'], cartella, ist['title'],
                          ist.get('description'), '3', 'light'),
            ('cta_banner', {
                'title': cta['title'], 'description': cta.get('description', ''),
                'surface': 'brand-gradient',
                'primary_cta': {'label': cta['buttonText'],
                                'route': '/rota-space', 'page': None,
                                'external_url': ''},
            }),
        ]

        pagina = StandardPage.objects.filter(slug='partner', locale=locale).first()
        if pagina is None:
            pagina = StandardPage(title='Partner', slug='partner', locale=locale)
            home.add_child(instance=pagina)
        else:
            pagina.title = 'Partner'
        pagina.body = corpo
        pagina.save()
        pagina.save_revision().publish()

        self.stdout.write(self.style.SUCCESS(
            f'/partner creata con {len(corpo)} blocchi e '
            f'{CMSImage.objects.count()} immagini in libreria.'))
