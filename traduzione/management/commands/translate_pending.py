"""Traduce cio' che non ha ancora tutte le lingue.

Perche' un comando e non un lavoro dentro la richiesta: tradurre un articolo
lungo richiede secondi, e nessuno deve aspettarli premendo "Pubblica". Non
esiste una coda di lavori nel progetto — Redis c'e' ma e' il canale di
Channels, senza persistenza ne' ritentativi — quindi il posto giusto e' un
comando su cron, che si puo' rilanciare senza danni.

    python manage.py translate_pending
    python manage.py translate_pending --lingua en --forza
    python manage.py translate_pending --solo cms.StandardPage

Prima girava su quattro generi cablati nel codice. Ora gira su cio' che e'
dichiarato in `traducibili.py`, quindi copre anche le pagine del CMS, i menu e
le etichette dei tag — che prima non erano coperti affatto.
"""

from django.core.management.base import BaseCommand

from traduzione import lingue
from traduzione.motori import motore
from traduzione.percorsi import estrai
from traduzione.servizio import lingua_di_stesura, traduci, traduzione_di
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

        totale = 0
        for modello in da_fare:
            fatte = self._traduci_modello(modello, m, options)
            totale += fatte
            if fatte:
                self.stdout.write(f'  {etichetta(modello):32} {fatte}')

        self.stdout.write(self.style.SUCCESS(f'{totale} tradotte.'))

        from traduzione.models import Traduzione
        in_coda = Traduzione.objects.filter(needs_review=True).count()
        if in_coda:
            self.stdout.write(self.style.WARNING(
                f'In coda di revisione: {in_coda}. Si vedono da /cms/snippets/traduzione/traduzione/.'))

    def _traduci_modello(self, modello, m, options):
        qs = modello.objects.all().order_by('pk')
        # Gli articoli non pubblicati non si servono a nessuno: tradurli sarebbe
        # spesa per un testo che forse non vedra' mai la luce.
        if hasattr(modello, 'is_published'):
            qs = qs.filter(is_published=True)
        qs = qs.prefetch_related('traduzioni')
        if options['limite']:
            qs = qs[:options['limite']]

        fatte = 0
        for oggetto in qs:
            origine = lingua_di_stesura(oggetto)
            bersagli = ([options['lingua']] if options['lingua']
                        else lingue.altre_lingue(origine))
            for lingua in bersagli:
                if lingua == origine:
                    continue
                try:
                    prima = traduzione_di(oggetto, lingua)
                    if (prima is not None and not options['forza']
                            and prima.e_aggiornata(estrai(oggetto))):
                        continue
                    if traduci(oggetto, lingua, m, forza=options['forza']):
                        fatte += 1
                except Exception as exc:
                    self.stderr.write(self.style.ERROR(
                        f'  {etichetta(modello)} #{oggetto.pk} -> {lingua}: {exc}'))
        return fatte
