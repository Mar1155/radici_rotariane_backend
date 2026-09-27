"""Le lingue di partenza.

Un database vuoto non ha lingue, e senza lingue non si traduce niente.

**Perche' queste sei e non altre.** Questa piattaforma serve i rotariani di
origine italiana nel mondo, quindi le lingue che contano sono quelle dei paesi
dove la diaspora italiana e' andata — le stesse dei club esteri fra i dati di
prova:

    en  Stati Uniti, Canada, Australia, Regno Unito
    es  Argentina, Uruguay, Venezuela — la comunita' italiana piu' grande fuori
        dall'Italia sta a Buenos Aires
    pt  Brasile — San Paolo ha piu' discendenti di italiani di qualunque altra
        citta' al mondo
    fr  Francia, Belgio, Svizzera romanda, Quebec
    de  Germania, Svizzera tedesca, Austria

Non e' un elenco delle lingue piu' parlate al mondo: il cinese e l'arabo hanno
piu' parlanti dello spagnolo e non c'entrano niente con questo sito.

Aggiungerne una qui non basta a farla comparire nel selettore: servono anche le
etichette dell'app, che stanno nel repository del frontend. Il perche' e il come
sono in `DEPLOY.md`.
"""

from django.core.management.base import BaseCommand

from traduzione.models import Lingua

LINGUE = [
    ('it', 'Italiano', 0),
    ('en', 'English', 1),
    ('es', 'Espanol', 2),
    ('pt', 'Portugues', 3),
    ('fr', 'Francais', 4),
    ('de', 'Deutsch', 5),
]


class Command(BaseCommand):
    help = 'Crea le lingue di partenza.'

    def handle(self, *args, **options):
        for codice, nome, ordine in LINGUE:
            _, creata = Lingua.objects.get_or_create(
                codice=codice, defaults={'nome': nome, 'ordine': ordine})
            if creata:
                self.stdout.write(f'  {codice}  {nome}')
        attive = Lingua.objects.filter(attiva=True).count()
        self.stdout.write(self.style.SUCCESS(
            f'{attive} lingue attive. Per aggiungerne altre: /cms/ -> Struttura -> Lingue.'))
