"""Le lingue di partenza.

Un database vuoto non ha lingue, e senza lingue non si traduce niente. Queste
due sono il minimo: l'italiano perche' e' la lingua in cui si scrive, l'inglese
perche' e' quella che serve a chi legge da fuori. Le altre si aggiungono da
`/cms/`, una riga alla volta, senza deploy.
"""

from django.core.management.base import BaseCommand

from traduzione.models import Lingua

LINGUE = [
    ('it', 'Italiano', 0),
    ('en', 'English', 1),
]


class Command(BaseCommand):
    help = 'Crea le lingue di partenza (italiano e inglese).'

    def handle(self, *args, **options):
        for codice, nome, ordine in LINGUE:
            _, creata = Lingua.objects.get_or_create(
                codice=codice, defaults={'nome': nome, 'ordine': ordine})
            if creata:
                self.stdout.write(f'  {codice}  {nome}')
        attive = Lingua.objects.filter(attiva=True).count()
        self.stdout.write(self.style.SUCCESS(
            f'{attive} lingue attive. Per aggiungerne altre: /cms/ -> Struttura -> Lingue.'))
