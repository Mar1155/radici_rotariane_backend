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

# Il nome di una lingua si scrive **nella lingua stessa**: chi cerca la sua non
# cerca "Spagnolo", cerca "Español". Per questo non sono tradotti e per questo
# vanno scritti con i loro accenti — senza, il selettore e' la prima cosa che un
# visitatore straniero vede scritta male.
LINGUE = [
    ('it', 'Italiano', 0),
    ('en', 'English', 1),
    ('es', 'Español', 2),
    ('pt', 'Português', 3),
    ('fr', 'Français', 4),
    ('de', 'Deutsch', 5),
]


class Command(BaseCommand):
    help = 'Crea le lingue di partenza.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--rinomina', action='store_true',
            help='Riscrive anche il nome delle lingue che esistono gia.')

    def handle(self, *args, **options):
        for codice, nome, ordine in LINGUE:
            riga, creata = Lingua.objects.get_or_create(
                codice=codice, defaults={'nome': nome, 'ordine': ordine})
            if creata:
                self.stdout.write(f'  {codice}  {nome}')
                continue
            # Il nome di una riga che c'e' gia' si riscrive **solo se richiesto**,
            # e la ragione e' che le due regole sensate sono in conflitto: chi
            # amministra puo' rinominare una lingua dal pannello e il comando
            # deve rispettarlo; ma un nome sbagliato spedito da noi — "Espanol"
            # senza tilde, arrivato in produzione — con il solo `get_or_create`
            # era definitivo, perche' nessuna riesecuzione lo toccava.
            #
            # Il conflitto si scioglie chiedendolo: senza `--rinomina` vince chi
            # amministra, con `--rinomina` vincono i nomi di qui. `attiva` e
            # `ordine` non si toccano in nessun caso: quelle sono scelte sue.
            if options['rinomina'] and riga.nome != nome:
                riga.nome = nome
                riga.save(update_fields=['nome'])
                self.stdout.write(f'  {codice}  {nome}  (rinominata)')
        attive = Lingua.objects.filter(attiva=True).count()
        self.stdout.write(self.style.SUCCESS(
            f'{attive} lingue attive. Per aggiungerne altre: /cms/ -> Struttura -> Lingue.'))
