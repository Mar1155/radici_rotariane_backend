"""Traduce cio' che non ha ancora tutte le lingue: articoli, post, commenti,
messaggi.

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

from chat.models import Message, MessageTranslation
from forum.models import Comment, CommentTranslation, Post, PostTranslation
from section.models import Card, CardTranslation
from traduzione.articoli import lingue_di_destinazione, traduci_articolo
from traduzione.conversazioni import (lingue_per, traduci_commento,
                                      traduci_messaggio, traduci_post)
from traduzione import lingue
from traduzione.motori import motore


class Command(BaseCommand):
    help = 'Traduce cio che non ha ancora tutte le lingue.'

    def add_arguments(self, parser):
        parser.add_argument('--lingua', help='Solo questa lingua.')
        parser.add_argument('--forza', action='store_true',
                            help='Ritraduce anche cio che e gia tradotto '
                                 '(le correzioni a mano restano intatte).')
        parser.add_argument('--limite', type=int, default=0,
                            help='Al massimo N oggetti per genere, per provare.')
        parser.add_argument('--solo', choices=['articoli', 'post', 'commenti',
                                               'messaggi'],
                            help='Un genere solo.')

    def handle(self, *args, **options):
        m = motore()
        self.stdout.write(f'Motore: {m.nome}')
        if m.da_rivedere:
            self.stdout.write(self.style.WARNING(
                'Le traduzioni prodotte finiranno nella coda di revisione.'))

        registrate = lingue.codici_attivi()
        if options['lingua'] and options['lingua'] not in registrate:
            self.stderr.write(self.style.ERROR(
                f'Lingua {options["lingua"]} non registrata. Ci sono: {registrate}'))
            return

        # (nome, queryset, funzione, modello-traduzione, campo-di-collegamento)
        GENERI = [
            ('articoli', Card.objects.filter(is_published=True).order_by('id'),
             traduci_articolo, CardTranslation, 'card'),
            ('post', Post.objects.order_by('id'),
             traduci_post, PostTranslation, 'post'),
            ('commenti', Comment.objects.order_by('created_at'),
             traduci_commento, CommentTranslation, 'comment'),
            ('messaggi', Message.objects.exclude(body='').order_by('id'),
             traduci_messaggio, MessageTranslation, 'message'),
        ]

        totali = {'fatte': 0, 'saltate': 0, 'fallite': 0}
        for nome, queryset, funzione, modello, campo in GENERI:
            if options['solo'] and options['solo'] != nome:
                continue
            if options['limite']:
                queryset = queryset[:options['limite']]

            for oggetto in queryset:
                origine = getattr(oggetto, 'source_locale', 'it') or 'it'
                da_fare = ([options['lingua']] if options['lingua']
                           else lingue_per(origine))
                for lingua in da_fare:
                    if lingua == origine:
                        continue
                    if not options['forza'] and modello.objects.filter(
                            **{campo: oggetto, 'target_language': lingua}).exists():
                        totali['saltate'] += 1
                        continue
                    try:
                        if funzione(oggetto, lingua, m):
                            totali['fatte'] += 1
                    except Exception as e:
                        totali['fallite'] += 1
                        self.stderr.write(self.style.ERROR(
                            f'  {nome} #{oggetto.pk} -> {lingua}: {e}'))
            self.stdout.write(f'  {nome}: fatto')

        riga = f"{totali['fatte']} tradotte"
        if totali['saltate']:
            riga += f", {totali['saltate']} gia presenti"
        if totali['fallite']:
            riga += f", {totali['fallite']} non riuscite"
        self.stdout.write(self.style.SUCCESS(riga + '.'))

        rimaste = sum(m_.objects.filter(needs_review=True).count()
                      for m_ in (CardTranslation, PostTranslation,
                                 CommentTranslation, MessageTranslation))
        if rimaste:
            self.stdout.write(
                f'In coda di revisione: {rimaste}. Si vedono da /admin/.')
