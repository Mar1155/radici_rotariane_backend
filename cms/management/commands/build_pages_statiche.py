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

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from wagtail.models import Locale

from cms.bootstrap import assicura_homepage
from cms.models import CMSImage, StandardPage

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


def spiega(errore, dove: str = '') -> list[str]:
    """Srotola un errore di StreamField in righe leggibili.

    Wagtail annida gli errori come sono annidati i blocchi, e in cima dice solo
    "Validation error in StreamBlock" — vero e inutile. Qui diventa
    `[3][items][0][icon]: MessageCircle non e' tra quelle disponibili`, che dice
    quale blocco e quale campo, ed e' l'unica forma in cui il messaggio serve a
    qualcosa.
    """
    annidati = getattr(errore, 'block_errors', None)
    if isinstance(annidati, dict):
        return [r for k, v in annidati.items() if v is not None
                for r in spiega(v, f'{dove}[{k}]')]
    if isinstance(annidati, list):
        return [r for i, v in enumerate(annidati) if v is not None
                for r in spiega(v, f'{dove}[{i}]')]
    if len(getattr(errore, 'error_list', [])) > 1:
        return [r for v in errore.error_list for r in spiega(v, dove)]
    messaggi = getattr(errore, 'messages', None) or [str(errore)]
    return [f'{dove or "(pagina)"}: {" ".join(messaggi)}']


def verifica(corpo, modello=None) -> list[str]:
    """Cio' che i blocchi rifiutano di questo contenuto. Vuoto se va bene.

    Serve perche' assegnare un corpo a uno StreamField **non lo valida**: il
    JSON grezzo entra nel database qualunque cosa contenga. Un'icona che non
    esiste nel vocabolario dava il guasto peggiore possibile — la pagina si
    costruiva, il comando diceva "pubblicate", sul sito il blocco non si
    vedeva, e aprendo la pagina nel pannello la tendina era vuota e la
    pubblicazione fallita. Tre sintomi lontani dalla causa, e nessun errore.
    """
    from cms.models import StandardPage
    blocco = (modello or StandardPage)._meta.get_field('body').stream_block
    try:
        blocco.clean(blocco.to_python(corpo))
    except ValidationError as errore:
        return spiega(errore)
    return []


PAGINE = [
    ('partner', 'Partner e Sponsor'),
    ('cip', 'Comitati Inter-Paese'),
    # Si chiamava "Radici Rotariane nel Mondo", che e' il nome del progetto
    # intero e confliggeva con la pagina della mappa: tre nomi per la stessa
    # cosa (menu, titolo, indirizzo) e nessuno la riconosceva.
    ('progetto', 'Chi siamo'),
    # Le tre pagine che erano codice. Stanno qui e non in un comando nuovo
    # perche' il JSON porta gli id dei blocchi: ricostruirle non butta via le
    # traduzioni, cosa che invece fa un corpo generato da tuple Python.
    ('rota-space', 'Rota-Space'),
    ('skills', 'Skills Network'),
    ('rotariani-nel-mondo', 'Rotariani nel Mondo'),
]


class Command(BaseCommand):
    help = 'Crea (o aggiorna) le pagine a contenuto versionato in cms/contenuti/.'

    @transaction.atomic
    def handle(self, *args, **options):
        locale = Locale.get_default()
        home = assicura_homepage()

        immagini = {i.title: i.pk for i in CMSImage.objects.all()}
        mancanti = set()

        for slug, titolo in PAGINE:
            file = CONTENUTI / f'{slug}.json'
            if not file.exists():
                self.stderr.write(self.style.WARNING(f'  manca {file.name}, salto /{slug}'))
                continue
            corpo = json.loads(file.read_text(encoding='utf-8'))
            corpo = risolvi_immagini(corpo, immagini, mancanti)

            problemi = verifica(corpo)
            if problemi:
                raise CommandError(
                    f'{file.name} contiene valori che i blocchi non accettano. '
                    'Non lo scrivo: finirebbe nel database senza che nessuno se '
                    'ne accorga, e la pagina sarebbe invisibile sul sito e non '
                    'pubblicabile dal pannello.\n  '
                    + '\n  '.join(problemi))

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
