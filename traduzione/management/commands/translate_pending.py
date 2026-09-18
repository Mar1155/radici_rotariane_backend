"""Traduce gli articoli pubblicati che non hanno ancora tutte le lingue.

Perche' un comando e non un lavoro dentro la richiesta: tradurre un articolo
lungo richiede secondi, e nessuno deve aspettarli premendo "Pubblica". Non
esiste una coda di lavori nel progetto — Redis c'e' ma e' il canale di Channels,
senza persistenza ne' ritentativi — quindi il posto giusto e' un comando su
cron, che si puo' rilanciare senza danni.

    python manage.py translate_pending
    python manage.py translate_pending --lingua en --forza
"""

from django.conf import settings
from django.core.management.base import BaseCommand

from section.models import Card, CardTranslation
from traduzione.articoli import lingue_di_destinazione, traduci_articolo
from traduzione.motori import motore


class Command(BaseCommand):
    help = 'Traduce gli articoli pubblicati a cui manca una lingua.'

    def add_arguments(self, parser):
        parser.add_argument('--lingua', help='Solo questa lingua.')
        parser.add_argument('--forza', action='store_true',
                            help='Ritraduce anche cio che e gia tradotto '
                                 '(le correzioni a mano restano intatte).')
        parser.add_argument('--limite', type=int, default=0,
                            help='Al massimo N articoli, per provare.')

    def handle(self, *args, **options):
        m = motore()
        self.stdout.write(f'Motore: {m.nome}')
        if m.da_rivedere:
            self.stdout.write(self.style.WARNING(
                'Le traduzioni prodotte finiranno nella coda di revisione.'))

        registrate = [c for c, _ in settings.WAGTAIL_CONTENT_LANGUAGES]
        if options['lingua'] and options['lingua'] not in registrate:
            self.stderr.write(self.style.ERROR(
                f'Lingua {options["lingua"]} non registrata. Ci sono: {registrate}'))
            return

        articoli = Card.objects.filter(is_published=True).order_by('id')
        if options['limite']:
            articoli = articoli[:options['limite']]

        fatte = saltate = fallite = 0
        for card in articoli:
            lingue = ([options['lingua']] if options['lingua']
                      else lingue_di_destinazione(card))
            for lingua in lingue:
                if lingua == (card.source_locale or 'it'):
                    continue
                if not options['forza'] and CardTranslation.objects.filter(
                        card=card, target_language=lingua).exists():
                    saltate += 1
                    continue
                try:
                    if traduci_articolo(card, lingua, m):
                        fatte += 1
                        self.stdout.write(f'  {card.slug} -> {lingua}')
                except Exception as e:
                    fallite += 1
                    self.stderr.write(self.style.ERROR(
                        f'  {card.slug} -> {lingua}: {e}'))

        riga = f'{fatte} tradotte'
        if saltate:
            riga += f', {saltate} gia presenti'
        if fallite:
            riga += f', {fallite} non riuscite'
        self.stdout.write(self.style.SUCCESS(riga + '.'))

        rimaste = CardTranslation.objects.filter(needs_review=True).count()
        if rimaste:
            self.stdout.write(
                f'In coda di revisione: {rimaste}. Si vedono da /admin/.')
