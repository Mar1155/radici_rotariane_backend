"""Traduce cio' che non ha ancora tutte le lingue.

**Non serve metterlo su cron.** Il server traduce da solo: cio' che viene
pubblicato finisce in coda e diventa tradotto in pochi secondi, e all'avvio il
processo recupera quello che era rimasto indietro. Questo comando resta per le
volte in cui si vuole decidere a mano:

    python manage.py translate_pending                  # tutto cio' che manca
    python manage.py translate_pending --lingua en --forza
    python manage.py translate_pending --solo cms.StandardPage
    python manage.py translate_pending --limite 20      # per provare, e vedere quanto costa

Ed e' il modo di tradurre dopo un `build_site` o un `seed_*`: i comandi di
gestione non accendono la coda, apposta — creano centinaia di oggetti in un
colpo, e si metterebbero a tradurre l'intero sito per poi morire a meta'.
"""

from django.core.management.base import BaseCommand

from traduzione import lingue, lucchetto
from traduzione.arretrati import traduci_arretrati
from traduzione.motori import motore
from traduzione.traducibili import TRADUCIBILI, etichetta, modelli


class Command(BaseCommand):
    help = 'Traduce cio che non ha ancora tutte le lingue.'

    def add_arguments(self, parser):
        parser.add_argument('--lingua', help='Solo questa lingua.')
        parser.add_argument('--forza', action='store_true',
                            help='Ritraduce anche cio che e gia tradotto '
                                 '(le correzioni a mano restano intatte).')
        parser.add_argument('--limite', type=int, default=0,
                            help='Al massimo N oggetti per modello, per provare.')
        parser.add_argument('--solo', help='Un modello solo, es. section.Card.')

    def handle(self, *args, **options):
        with lucchetto.preso() as nostro:
            if not nostro:
                self.stderr.write(self.style.ERROR(
                    'Un altro giro di traduzioni e gia in corso: mi fermo qui.\n'
                    'Due giri insieme traducono le stesse cose e le pagano due '
                    'volte. Aspetta che finisca, oppure fermalo.'))
                return
            self.lavora(options)

    def lavora(self, options):
        m = motore()
        self.stdout.write(f'Motore: {m.nome}')
        if m.da_rivedere:
            self.stdout.write(self.style.WARNING(
                'Le traduzioni prodotte finiranno nella coda di revisione.'))

        registrate = lingue.codici_attivi()
        if options['lingua'] and options['lingua'] not in registrate:
            self.stderr.write(self.style.ERROR(
                f'Lingua {options["lingua"]} non attiva. Ci sono: {registrate}'))
            return

        da_fare = modelli()
        if options['solo']:
            da_fare = [x for x in da_fare if etichetta(x) == options['solo']]
            if not da_fare:
                self.stderr.write(self.style.ERROR(
                    f'{options["solo"]} non e dichiarato. Ci sono: '
                    f'{", ".join(sorted(TRADUCIBILI))}'))
                return

        fatte = traduci_arretrati(
            m, lingua=options['lingua'], forza=options['forza'],
            limite=options['limite'], da_fare=da_fare, su_errore=self.dillo)

        for nome, quante in fatte.items():
            self.stdout.write(f'  {nome:32} {quante}')
        self.stdout.write(self.style.SUCCESS(f'{sum(fatte.values())} tradotte.'))

        from traduzione.models import Traduzione
        in_coda = Traduzione.objects.filter(needs_review=True).count()
        if in_coda:
            self.stdout.write(self.style.WARNING(
                f'In coda di revisione: {in_coda}. Si vedono da '
                f'/cms/snippets/traduzione/traduzione/.'))

    def dillo(self, modello, pk, lingua, errore):
        self.stderr.write(self.style.ERROR(f'  {modello} #{pk} -> {lingua}: {errore}'))
