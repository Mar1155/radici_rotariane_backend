"""Cio' che e' dichiarato traducibile si traduce quando viene salvato.

Prima lo facevano quattro chiamate scritte a mano dentro le viste del forum e
della chat. Il risultato era che post, commenti e messaggi si traducevano
subito, e **articoli, pagine, menu e tipi di articolo no**: quelli aspettavano
il comando su cron. Cioe' proprio il contenuto che scrive l'admin — l'unica
persona per cui questo progetto e' stato generalizzato — era l'unico a
rimanere indietro.

Qui la regola e' una sola e vale per tutti: se un modello sta in `TRADUCIBILI`,
salvarlo lo mette in coda. Aggiungere un modello traducibile domani non
richiede di ricordarsi anche di questo file.

Le pagine sono l'eccezione, e per un motivo preciso: si salvano in bozza molte
volte prima di essere pubblicate, e una bozza non la legge nessuno. Per quelle
il segnale giusto e' la pubblicazione.
"""

from __future__ import annotations

from django.db.models.signals import post_save
from wagtail.models import Page
from wagtail.signals import page_published

from traduzione import coda
from traduzione.models import Lingua
from traduzione.traducibili import modelli


def _salvato(sender, instance, **kwargs):
    coda.accoda(instance)


def _pubblicata(sender, instance, **kwargs):
    # `instance` e' gia' la pagina specifica, ma non costa niente esserne certi:
    # una `Page` generica non ha i campi che si traducono.
    coda.accoda(getattr(instance, 'specific', instance))


def _lingua_cambiata(sender, instance, **kwargs):
    """Una lingua nuova non fa salvare nessun contenuto, quindi nessun
    salvataggio farebbe da innesco: il ripasso lo chiede lei."""
    coda.recupera()


def collega() -> None:
    """Attacca i segnali. La chiama `TraduzioneConfig.ready()`."""
    post_save.connect(_lingua_cambiata, sender=Lingua,
                      dispatch_uid='traduzione:lingua')
    for modello in modelli():
        if issubclass(modello, Page):
            continue
        post_save.connect(_salvato, sender=modello,
                          dispatch_uid=f'traduzione:{modello._meta.label_lower}')
    page_published.connect(_pubblicata, dispatch_uid='traduzione:page_published')
