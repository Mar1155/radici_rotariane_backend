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

from traduzione import lingue
from traduzione.models import Traduzione, impronta
from traduzione.motori import MotoreIdentita, MotoreTraduzione, motore
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


def traduzione_di(oggetto, lingua: str, fresca: bool = False):
    """La riga di traduzione, se c'e'. Usa il prefetch quando c'e' stato.

    `fresca` scavalca il prefetch e chiede al database. Serve prima di pagare
    una traduzione: il prefetch e' una fotografia scattata quando la lista e'
    stata letta, e un comando che macina migliaia di oggetti ci mette minuti ad
    arrivare in fondo. Se in quei minuti qualcun altro ha scritto la stessa
    riga — il cron, il thread di sottofondo, un secondo comando lanciato a mano
    — la fotografia non lo mostra.
    """
    if fresca:
        return oggetto.traduzioni.filter(target_language=lingua).first()
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


def e_allineata(esistente, sorgente: dict, m: MotoreTraduzione) -> bool:
    """Se la riga che c'e' gia' e' una traduzione vera, e di questo originale.

    Due condizioni, non una. L'impronta dice che l'originale non e' cambiato.
    Il `provider` dice che qualcuno l'ha davvero tradotta: una riga scritta dal
    motore di identita' **contiene l'originale**, e il confronto delle impronte
    la dichiarerebbe a posto per sempre. Senza questa seconda condizione, un
    solo giro di cron senza motore configurato congela il sito nella lingua di
    stesura, e configurare il motore dopo non basta piu': servirebbe `--forza`,
    che nessuno sa di dover dare perche' il comando non segnala niente.
    """
    if not esistente.e_aggiornata(sorgente):
        return False
    return not (esistente.provider == MotoreIdentita.nome
                and m.nome != MotoreIdentita.nome)


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

    m = m or motore()
    esistente = traduzione_di(oggetto, lingua)
    if esistente is None:
        # Una query per non pagare una traduzione che esiste gia'.
        esistente = traduzione_di(oggetto, lingua, fresca=True)
    if esistente is not None and not forza and e_allineata(esistente, sorgente, m):
        return esistente

    richiesti = da_tradurre(oggetto, esistente, sorgente)
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
        # `get_or_create` e non `create`: fra il controllo di poco fa e questa
        # riga c'e' stata la chiamata al motore, che dura secondi, e in quei
        # secondi un altro processo puo' aver scritto la stessa traduzione. Con
        # `create` il vincolo di unicita' lo trasforma in un errore per ogni
        # oggetto e per ogni lingua, e il lavoro fatto si butta via.
        esistente, creata = Traduzione.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(oggetto),
            object_id=str(oggetto.pk),
            target_language=lingua,
            defaults={'locked_paths': [], **valori})
        if creata:
            return esistente
        # C'era. Le frasi che nel frattempo qualcuno ha corretto a mano vincono
        # su quelle appena tradotte: e' la stessa regola di `da_tradurre`,
        # applicata a una riga che quando abbiamo deciso non esisteva.
        bloccati = set(esistente.locked_paths or [])
        valori['texts'] = {**valori['texts'],
                           **{k: v for k, v in (esistente.texts or {}).items()
                              if k in bloccati}}

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
    """Traduce senza far aspettare chi ha scritto: mette in coda e torna.

    Resta come nome perche' e' cosi' che la chiamano le viste, ma il lavoro
    vero sta in `coda.py`. Prima apriva un thread per oggetto; adesso la coda
    ne tiene uno solo, e chi arriva dopo aspetta il suo turno invece di
    chiamare il modello tutti insieme.
    """
    from traduzione import coda
    coda.accoda(oggetto)
