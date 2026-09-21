"""Le lingue in cui il sito si legge, e le traduzioni dei contenuti.

Prima erano due elenchi: una variabile d'ambiente (`CONTENT_LANGUAGES`) e la
tabella `Locale` di Wagtail. Due fonti per la stessa cosa significano che
aggiungere una lingua non e' mai un gesto solo, e che possono divergere — si
poteva tradurre una chat in spagnolo mentre il sito lo spagnolo non ce l'aveva.

Qui la fonte e' una: una riga in questa tabella, aggiunta dal pannello.
"""

import hashlib
import json

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
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


def impronta(testi: dict) -> str:
    """L'impronta dei testi di partenza.

    Serve a sapere se l'originale e' cambiato da quando si e' tradotto: senza,
    una traduzione non veniva mai rinfrescata e modificare un articolo lasciava
    l'inglese fermo per sempre.
    """
    grezzo = json.dumps(testi or {}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(grezzo.encode('utf-8')).hexdigest()


class Traduzione(models.Model):
    """Un contenuto in un'altra lingua.

    Una riga per (oggetto, lingua), qualunque sia l'oggetto: un articolo, un
    commento, una pagina del CMS, l'etichetta di un tag. Prima erano quattro
    tabelle identiche piu' un JSONField piu' wagtail-localize, cioe' sei modi
    di rispondere alla stessa domanda.

    **`texts` e' una mappa percorso -> testo, non i valori dei campi.** La
    differenza conta: tenendo il documento intero, aggiungere un paragrafo
    all'originale lasciava la traduzione a com'era, e il lettore inglese non
    vedeva il paragrafo nuovo. Tenendo i testi per percorso, la struttura e'
    sempre quella corrente dell'oggetto e un percorso senza traduzione ricade
    sull'originale: il paragrafo compare subito in italiano dentro una pagina
    inglese, e diventa inglese al giro dopo.
    """

    PROVIDER_CHOICES = [
        ('claude', 'Modello linguistico'),
        ('identita', 'Nessuna traduzione (testo originale)'),
        ('umano', 'Scritta da una persona'),
    ]

    # `object_id` e' testuale perche' le chiavi primarie non concordano: Card,
    # Message e i modelli del CMS hanno id interi, Post, Comment e Chat hanno
    # UUID. Django converte con str(pk) in scrittura e nei filtri, quindi le
    # due forme convivono senza colonne parallele. Si perde il vincolo di
    # integrita' nel database: lo compensa la GenericRelation su ogni modello
    # traducibile, che e' cio' che fa sparire le traduzioni con l'oggetto.
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=64)
    oggetto = GenericForeignKey('content_type', 'object_id')

    target_language = models.CharField(max_length=10, verbose_name='lingua')
    source_language = models.CharField(max_length=10, verbose_name='lingua di stesura')

    texts = models.JSONField(default=dict, blank=True, verbose_name='testi')
    # I percorsi corretti a mano. Bloccare per percorso invece che per oggetto
    # e' cio' che permette di correggere una frase senza congelare le altre
    # quaranta: prima `human_locked` fermava la ritraduzione di tutto.
    locked_paths = models.JSONField(default=list, blank=True,
                                    verbose_name='percorsi bloccati')
    human_locked = models.BooleanField(default=False, verbose_name='corretta a mano')
    needs_review = models.BooleanField(default=False, db_index=True,
                                       verbose_name='da rivedere')
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, blank=True)
    source_digest = models.CharField(max_length=64, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'traduzione'
        verbose_name_plural = 'traduzioni'
        ordering = ['-needs_review', '-updated_at']
        constraints = [
            models.UniqueConstraint(
                fields=['content_type', 'object_id', 'target_language'],
                name='uniq_traduzione_oggetto_lingua'),
        ]
        indexes = [
            models.Index(fields=['content_type', 'object_id', 'target_language']),
            models.Index(fields=['target_language', 'needs_review']),
        ]

    def __str__(self):
        return f'{self.content_type.model} #{self.object_id} -> {self.target_language}'

    def save(self, *args, **kwargs):
        # Derivato, non indipendente: due letture della stessa cosa divergono.
        self.human_locked = bool(self.locked_paths)
        super().save(*args, **kwargs)

    def e_aggiornata(self, testi_sorgente: dict) -> bool:
        """Se la traduzione corrisponde all'originale di adesso."""
        return bool(self.source_digest) and self.source_digest == impronta(testi_sorgente)
