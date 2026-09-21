"""Le lingue in cui il sito si legge.

Prima erano due elenchi: una variabile d'ambiente (`CONTENT_LANGUAGES`) e la
tabella `Locale` di Wagtail. Due fonti per la stessa cosa significano che
aggiungere una lingua non e' mai un gesto solo, e che possono divergere — si
poteva tradurre una chat in spagnolo mentre il sito lo spagnolo non ce l'aveva.

Qui la fonte e' una: una riga in questa tabella, aggiunta dal pannello.
"""

from django.db import models


class Lingua(models.Model):
    """Una lingua in cui i contenuti vengono serviti.

    Aggiungerne una e' una riga da `/cms/`. Al primo giro di
    `translate_pending` tutto cio' che non ce l'ha viene tradotto, perche' il
    ciclo e' gia' "tutte le lingue registrate tranne la propria": nessuna
    migrazione, nessun comando da inventare.
    """

    codice = models.CharField(
        max_length=10, unique=True, verbose_name='codice',
        help_text='Codice ISO 639-1: it, en, es, fr...')
    # L'endonimo, cioe' il nome della lingua nella lingua stessa: e' quello che
    # riconosce chi la parla, ed e' quello che si mette in un selettore.
    nome = models.CharField(
        max_length=60, verbose_name='nome',
        help_text='Il nome nella lingua stessa: Italiano, English, Espanol.')
    attiva = models.BooleanField(
        default=True, verbose_name='attiva',
        help_text='Se spenta, il sito smette di servirla e di tradurre verso '
                  'di essa. Le traduzioni gia fatte restano.')
    ordine = models.IntegerField(default=0, verbose_name='ordine')

    class Meta:
        ordering = ['ordine', 'codice']
        verbose_name = 'lingua'
        verbose_name_plural = 'lingue'

    def __str__(self):
        return f'{self.nome} ({self.codice})'

    def save(self, *args, **kwargs):
        self.codice = (self.codice or '').strip().lower()
        super().save(*args, **kwargs)
