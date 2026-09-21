"""Tradurre cio' che le persone si scrivono: forum e chat.

Lo stesso motore e lo stesso glossario degli articoli. Prima questi due
passavano da un servizio di traduzione separato, con due chiavi diverse e
nessun glossario: un post che parlava di "Azione internazionale" veniva
tradotto alla lettera, mentre lo stesso termine in un articolo no.

La differenza con gli articoli resta nel **quando**, non nel come:
- un post o un commento si traducono quando vengono pubblicati;
- un messaggio di chat quando viene inviato, in un thread a parte, perche'
  nessuno deve aspettare la traduzione per veder partire il proprio messaggio.
"""

from __future__ import annotations

import logging

from django.conf import settings

from traduzione import lingue
from django.db import close_old_connections, transaction

from .motori import MotoreTraduzione, motore

logger = logging.getLogger(__name__)


def lingue_per(lingua_origine: str) -> list[str]:
    """Tutte le lingue registrate tranne quella di partenza."""
    return lingue.altre_lingue(lingua_origine)


def _traduci_campi(testi: dict[str, str], da: str, a: str, m: MotoreTraduzione):
    return m.traduci(testi, da=da, a=a) if testi else {}


# --- Forum -------------------------------------------------------------------

def traduci_post(post, lingua: str, m: MotoreTraduzione | None = None):
    from forum.models import PostTranslation

    esistente = PostTranslation.objects.filter(
        post=post, target_language=lingua).first()
    if esistente and esistente.human_locked:
        return esistente

    m = m or motore()
    testi = {k: v for k, v in
             {'title': post.title, 'description': post.description}.items() if v}
    if not testi:
        return None
    tradotti = _traduci_campi(testi, post.source_locale or 'it', lingua, m)

    traduzione, _ = PostTranslation.objects.update_or_create(
        post=post, target_language=lingua,
        defaults={
            'translated_title': tradotti.get('title', ''),
            'translated_description': tradotti.get('description', ''),
            'provider': m.nome,
            'detected_source_language': post.source_locale or 'it',
            'needs_review': m.da_rivedere,
            'human_locked': False,
        })
    return traduzione


def traduci_commento(commento, lingua: str, m: MotoreTraduzione | None = None):
    from forum.models import CommentTranslation

    esistente = CommentTranslation.objects.filter(
        comment=commento, target_language=lingua).first()
    if esistente and esistente.human_locked:
        return esistente
    if not commento.text:
        return None

    m = m or motore()
    tradotti = _traduci_campi({'text': commento.text},
                              commento.source_locale or 'it', lingua, m)
    traduzione, _ = CommentTranslation.objects.update_or_create(
        comment=commento, target_language=lingua,
        defaults={
            'translated_text': tradotti.get('text', ''),
            'provider': m.nome,
            'needs_review': m.da_rivedere,
            'human_locked': False,
        })
    return traduzione


# --- Chat --------------------------------------------------------------------

def traduci_messaggio(messaggio, lingua: str, m: MotoreTraduzione | None = None):
    from chat.models import MessageTranslation

    esistente = MessageTranslation.objects.filter(
        message=messaggio, target_language=lingua).first()
    if esistente and esistente.human_locked:
        return esistente
    if not messaggio.body:
        return None

    m = m or motore()
    tradotti = _traduci_campi({'text': messaggio.body},
                              messaggio.source_locale or 'it', lingua, m)
    traduzione, _ = MessageTranslation.objects.update_or_create(
        message=messaggio, target_language=lingua,
        defaults={
            'translated_text': tradotti.get('text', ''),
            'provider': m.nome,
            'detected_source_language': messaggio.source_locale or 'it',
            'needs_review': m.da_rivedere,
            'human_locked': False,
        })
    return traduzione


# --- Traduzione in tutte le lingue, senza far aspettare chi scrive -----------

_FUNZIONI = {
    'post': (traduci_post, 'source_locale'),
    'commento': (traduci_commento, 'source_locale'),
    'messaggio': (traduci_messaggio, 'source_locale'),
}


def traduci_tutto(genere: str, oggetto, m: MotoreTraduzione | None = None) -> int:
    """Traduce l'oggetto in tutte le lingue registrate. Torna quante ne ha fatte."""
    funzione, campo = _FUNZIONI[genere]
    m = m or motore()
    fatte = 0
    for lingua in lingue_per(getattr(oggetto, campo, 'it')):
        try:
            if funzione(oggetto, lingua, m):
                fatte += 1
        except Exception as e:
            logger.exception('Traduzione %s #%s in %s non riuscita: %s',
                             genere, oggetto.pk, lingua, e)
    return fatte


def traduci_in_sottofondo(genere: str, oggetto):
    """Traduce senza far aspettare chi ha scritto.

    Un thread e non una coda di lavori, perche' nel progetto non ce n'e' una:
    Redis c'e' ma e' il canale di Channels, senza persistenza ne' ritentativi.
    Il thread e' quindi **best effort** — se il processo si riavvia a meta', la
    traduzione si perde. La rete di sicurezza e' `translate_pending` su cron,
    che riprende tutto cio' che e' rimasto indietro.

    Parte al commit, non subito: il thread ha una connessione sua e non vede
    quello che la transazione di chi ha scritto non ha ancora confermato. Oggi
    le viste sono in autocommit e `on_commit` esegue all'istante, quindi non
    cambia niente; se un domani una vista finisse dentro una transazione,
    senza questo la traduzione cercherebbe una riga che non c'e' ancora.
    """
    import threading

    if not getattr(settings, 'TRADUZIONE_IN_SOTTOFONDO', True):
        return

    def lavora():
        try:
            close_old_connections()   # il thread ha la sua connessione
            traduci_tutto(genere, oggetto)
        except Exception:
            logger.exception('Traduzione in sottofondo non riuscita.')
        finally:
            close_old_connections()

    transaction.on_commit(lambda: threading.Thread(target=lavora, daemon=True).start())
