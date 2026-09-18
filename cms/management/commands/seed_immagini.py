"""Carica nel CMS le immagini a cui i contenuti versionati fanno riferimento.

Le pagine fisse citano le immagini **per titolo** (`"@Scintille"`), perche' le
chiavi numeriche non sopravvivono a un azzeramento. Ma il titolo da solo non
basta: il file deve esistere. Questo comando lo mette, cosi' un reset ricostruisce
anche i loghi invece di lasciare dei riquadri vuoti.

I file stanno in `cms/contenuti/immagini/`, versionati accanto al JSON che li
cita: se un domani il cliente cambia un logo, lo sostituisce li'.

Idempotente: un'immagine gia' presente con quel titolo non si ricarica.
"""

from pathlib import Path

from django.core.files.images import ImageFile
from django.core.management.base import BaseCommand
from django.db import transaction

from cms.models import CMSImage

IMMAGINI = Path(__file__).resolve().parent.parent.parent / 'contenuti' / 'immagini'

# titolo nel contenuto -> file
LOGHI = {
    'Scintille': 'scintille.png',
    'Fidia s.r.l.': 'fidia.png',
    'Zicarelli': 'zicarelli.png',
    'Gruppo Chiappetta': 'gruppo-chiappetta.svg',
    'Mauser Gas': 'mauser-gas.png',
    'Greenpipe': 'greenpipe.png',
    'Barci Engineering': 'barci-engineering.png',
    'Linea Immagine': 'linea-immagine.png',
}


class Command(BaseCommand):
    help = 'Carica le immagini citate dai contenuti versionati.'

    @transaction.atomic
    def handle(self, *args, **options):
        caricate = presenti = mancanti = 0

        for titolo, nome_file in LOGHI.items():
            if CMSImage.objects.filter(title=titolo).exists():
                presenti += 1
                continue
            percorso = IMMAGINI / nome_file
            if not percorso.exists():
                mancanti += 1
                self.stderr.write(self.style.WARNING(
                    f'  manca il file {nome_file} per "{titolo}"'))
                continue
            with percorso.open('rb') as f:
                immagine = CMSImage(title=titolo)
                immagine.file = ImageFile(f, name=nome_file)
                immagine.save()
            caricate += 1

        riga = f'{caricate} immagini caricate'
        if presenti:
            riga += f', {presenti} gia presenti'
        if mancanti:
            riga += f', {mancanti} senza file'
        self.stdout.write(self.style.SUCCESS(riga + '.'))
