"""Costruisce le pagine il cui contenuto e' fisso: /cip, /progetto, /partner.

Il contenuto vive in `cms/contenuti/*.json`, versionato accanto al codice.

Prima questi comandi prendevano il contenuto da file JSON estratti al volo dai
dizionari del frontend e passati con `--content`: una volta cancellati quei
file, le pagine non erano piu' ricostruibili. Con un azzeramento del database
in programma, un seed che dipende da file che non esistono piu' non e' un seed.

Idempotente.
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from wagtail.models import Locale

from cms.models import CMSImage, HomePage, StandardPage

CONTENUTI = Path(__file__).resolve().parent.parent.parent / 'contenuti'

def risolvi_immagini(nodo, immagini, mancanti):
    """Le immagini sono riferite per titolo, non per chiave numerica.

    Le chiavi non sopravvivono a un azzeramento del database; i titoli si',
    perche' li si reimposta al momento del caricamento.
    """
    if isinstance(nodo, dict):
        risolto = {}
        for k, v in nodo.items():
            if k in ('image', 'photo', 'logo') and isinstance(v, str) and v.startswith('@'):
                titolo = v[1:]
                if titolo in immagini:
                    risolto[k] = immagini[titolo]
                else:
                    mancanti.add(titolo)
                    risolto[k] = None
            else:
                risolto[k] = risolvi_immagini(v, immagini, mancanti)
        return risolto
    if isinstance(nodo, list):
        return [risolvi_immagini(x, immagini, mancanti) for x in nodo]
    return nodo


PAGINE = [
    ('partner', 'Partner e Sponsor'),
    ('cip', 'Comitati Inter-Paese'),
    ('progetto', 'Radici Rotariane nel Mondo'),
]


class Command(BaseCommand):
    help = 'Crea (o aggiorna) /partner, /cip e /progetto dai contenuti versionati.'

    @transaction.atomic
    def handle(self, *args, **options):
        locale = Locale.get_default()
        home = HomePage.objects.filter(locale=locale).first()
        if home is None:
            self.stderr.write(self.style.ERROR(
                'Manca la HomePage: esegui prima `build_page_home`.'))
            return

        immagini = {i.title: i.pk for i in CMSImage.objects.all()}
        mancanti = set()

        for slug, titolo in PAGINE:
            file = CONTENUTI / f'{slug}.json'
            if not file.exists():
                self.stderr.write(self.style.WARNING(f'  manca {file.name}, salto /{slug}'))
                continue
            corpo = json.loads(file.read_text(encoding='utf-8'))
            corpo = risolvi_immagini(corpo, immagini, mancanti)

            pagina = StandardPage.objects.filter(slug=slug, locale=locale).first()
            if pagina is None:
                pagina = StandardPage(title=titolo, slug=slug, locale=locale)
                home.add_child(instance=pagina)
            pagina.title = titolo
            pagina.body = json.dumps(corpo)
            pagina.save()
            pagina.save_revision().publish()
            self.stdout.write(f'  /{slug:12} {len(corpo)} blocchi')

        if mancanti:
            self.stdout.write(self.style.WARNING(
                '\nImmagini non trovate, i blocchi che le usano restano vuoti: '
                + ', '.join(sorted(mancanti))
                + '\nCaricale da /cms/ con esattamente questo titolo e rilancia.'))
        self.stdout.write(self.style.SUCCESS('Pagine statiche pubblicate.'))
