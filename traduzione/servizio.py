"""Tradurre un oggetto, qualunque oggetto.

Prima c'erano quattro funzioni — `traduci_articolo`, `traduci_post`,
`traduci_commento`, `traduci_messaggio` — che facevano la stessa cosa su
quattro modelli: estrarre i testi, mandarli al motore, salvare il risultato in
una tabella diversa per ciascuno. Qui e' una sola, e vale anche per le pagine
del CMS e per le etichette dei tag, che prima non erano coperte affatto.
"""

from __future__ import annotations

import logging

from django.contrib.contenttypes.models import ContentType
from django.db import close_old_connections, transaction

from traduzione import lingue
from traduzione.models import Traduzione, impronta
from traduzione.motori import MotoreTraduzione, motore
from traduzione.percorsi import estrai
from traduzione.traducibili import e_traducibile

logger = logging.getLogger(__name__)


def lingua_di_stesura(oggetto) -> str:
    """La lingua in cui l'oggetto e' stato scritto.

    Gli articoli e i messaggi la registrano; le pagine del CMS no, perche' si
    compongono sempre nella lingua del sito. Se un giorno servisse, e' una
    colonna in piu' su un modello, non un concetto nuovo.
    """
    from django.conf import settings
    return (getattr(oggetto, 'source_locale', None)
            or settings.LANGUAGE_CODE.split('-')[0])


def traduzione_di(oggetto, lingua: str):
    """La riga di traduzione, se c'e'. Usa il prefetch quando c'e' stato."""
    precaricate = getattr(oggetto, '_traduzioni_lingua', None)
    if precaricate is not None:
        return next((t for t in precaricate if t.target_language == lingua), None)
    return next((t for t in oggetto.traduzioni.all()
                 if t.target_language == lingua), None)


def da_tradurre(oggetto, esistente, sorgente: dict) -> dict[str, str]:
    """I testi che vanno mandati al motore.

    Non e' tutto: cio' che qualcuno ha corretto a mano resta com'e'. Il blocco
    e' **per percorso**, non per oggetto, ed e' la differenza che permette di
    sistemare una frase senza congelare le altre quaranta.
    """
    if esistente is None:
        return dict(sorgente)
    bloccati = set(esistente.locked_paths or [])
    return {k: v for k, v in sorgente.items() if k not in bloccati}


def traduci(oggetto, lingua: str, m: MotoreTraduzione | None = None,
            forza: bool = False) -> Traduzione | None:
    """Traduce un oggetto in una lingua. Restituisce la riga, o None.

    Non fa niente se la lingua e' quella di stesura, se l'oggetto non e'
    dichiarato traducibile, o se la traduzione e' gia' allineata all'originale.
    """
    if not e_traducibile(oggetto):
        return None

    origine = lingua_di_stesura(oggetto)
    if lingua == origine:
        return None

    sorgente = estrai(oggetto)
    if not sorgente:
        return None

    esistente = traduzione_di(oggetto, lingua)
    if esistente is not None and not forza and esistente.e_aggiornata(sorgente):
        return esistente

    richiesti = da_tradurre(oggetto, esistente, sorgente)
    m = m or motore()
    tradotti = m.traduci(richiesti, da=origine, a=lingua) if richiesti else {}

    # I percorsi bloccati mantengono la versione corretta a mano.
    testi = dict(esistente.texts) if esistente is not None else {}
    # Via i percorsi che nell'originale non ci sono piu': una traduzione non
    # deve conservare frasi che l'autore ha cancellato.
    testi = {k: v for k, v in testi.items() if k in sorgente}
    testi.update(tradotti)

    valori = {
        'source_language': origine,
        'texts': testi,
        'provider': m.nome,
        'needs_review': m.da_rivedere,
        'source_digest': impronta(sorgente),
    }
    if esistente is None:
        return Traduzione.objects.create(
            content_type=ContentType.objects.get_for_model(oggetto),
            object_id=str(oggetto.pk),
            target_language=lingua,
            locked_paths=[],
            **valori)

    for campo, valore in valori.items():
        setattr(esistente, campo, valore)
    esistente.save()
    return esistente


def traduci_tutto(oggetto, m: MotoreTraduzione | None = None, forza: bool = False):
    """Traduce un oggetto in tutte le lingue registrate tranne la sua."""
    m = m or motore()
    return [t for lingua in lingue.altre_lingue(lingua_di_stesura(oggetto))
            if (t := traduci(oggetto, lingua, m, forza)) is not None]


def traduci_in_sottofondo(oggetto):
    """Traduce senza far aspettare chi ha scritto.

    Un thread e non una coda di lavori, perche' nel progetto non ce n'e' una:
    Redis c'e' ma e' il canale di Channels, senza persistenza ne' ritentativi.
    Il thread e' quindi **best effort** — se il processo si riavvia a meta', la
    traduzione si perde. La rete di sicurezza e' `translate_pending` su cron.

    Parte al commit, non subito: il thread ha una connessione sua e non vede
    quello che la transazione di chi ha scritto non ha ancora confermato.
    """
    import threading

    from django.conf import settings
    if not getattr(settings, 'TRADUZIONE_IN_SOTTOFONDO', True):
        return

    def lavora():
        try:
            close_old_connections()
            traduci_tutto(oggetto)
        except Exception:
            logger.exception('Traduzione in sottofondo non riuscita.')
        finally:
            close_old_connections()

    transaction.on_commit(lambda: threading.Thread(target=lavora, daemon=True).start())
