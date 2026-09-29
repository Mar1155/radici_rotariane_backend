"""La coda delle traduzioni: una alla volta, in sottofondo, senza far aspettare.

Chi pubblica non deve aspettare la traduzione — sono secondi per lingua, e le
lingue sono cinque — ma nemmeno ritrovarsela a meta'. Quindi il salvataggio
mette l'oggetto in coda e torna subito, e un **solo** lavoratore la svuota.

Perche' uno solo e non un thread per salvataggio, che era il disegno di prima:

- dieci articoli pubblicati di fila aprivano dieci thread che chiamavano il
  modello insieme, e il servizio risponde 429 quando si esagera;
- ogni thread tiene una connessione al database aperta, e il numero di
  connessioni e' la risorsa piu' scarsa che abbiamo;
- e soprattutto non si sapeva mai quante traduzioni stessero girando.

Con una coda la risposta e' sempre la stessa: una. Le altre aspettano il loro
turno, e nel frattempo il sito e' gia' tornato a chi ha premuto "Pubblica".

**Non e' una coda di lavori persistente**, e non finge di esserlo: vive nella
memoria del processo, quindi un riavvio la perde. La rete di sicurezza e' il
recupero degli arretrati all'avvio (`arretrati.py`), che ripesca cio' che era
in coda quando il processo e' morto. Le due cose insieme coprono il caso che
conta: pubblichi, il container si riavvia, e la traduzione arriva lo stesso.
"""

from __future__ import annotations

import logging
import queue
import threading

from django.conf import settings
from django.db import close_old_connections, transaction

logger = logging.getLogger(__name__)

# (etichetta del modello, chiave primaria come stringa)
Chiave = tuple[str, str]

# Il compito che non e' un oggetto: recupera cio' che e' rimasto indietro.
RECUPERO: Chiave = ('', '')

_coda: queue.Queue[Chiave] = queue.Queue()
_in_attesa: set[Chiave] = set()
_guardia = threading.Lock()
_lavoratore: threading.Thread | None = None


def avvia() -> None:
    """Accende la coda. La chiama **solo** il server, da `backend/asgi.py`.

    E' anche l'interruttore che tiene fuori i comandi di gestione: `build_site`
    e i vari `seed_*` creano centinaia di oggetti in un colpo, e senza questo
    ogni `manage.py` si metterebbe a tradurre l'intero sito in sottofondo per
    poi morire a meta' quando il comando finisce. I comandi hanno il loro
    strumento, che e' `translate_pending`.

    `TRADUZIONE_IN_SOTTOFONDO=false` la tiene spenta anche sul server: il sito
    funziona, i contenuti restano nella lingua in cui sono scritti, e si
    traduce a mano quando si vuole. E' l'interruttore da usare se un giorno la
    spesa va fermata di colpo.
    """
    global _lavoratore
    if not getattr(settings, 'TRADUZIONE_IN_SOTTOFONDO', True):
        logger.warning('TRADUZIONE_IN_SOTTOFONDO e spenta: niente traduzioni automatiche.')
        return
    with _guardia:
        if _lavoratore is not None:
            return
        _lavoratore = threading.Thread(target=_lavora, name='traduzioni', daemon=True)
        _lavoratore.start()
    recupera()


def accesa() -> bool:
    return _lavoratore is not None


def accoda(oggetto) -> None:
    """Mette un oggetto in coda, se c'e' qualcosa da tradurre e se la coda e' accesa.

    Al commit e non subito: il lavoratore ha una connessione sua e non vede
    quello che la transazione di chi ha scritto non ha ancora confermato.

    Se lo stesso oggetto e' gia' in attesa non si accoda due volte. Salvare
    cinque volte di fila mentre si aggiusta un titolo produce **una**
    traduzione, non cinque: il lavoratore rilegge l'oggetto dal database quando
    arriva il suo turno, quindi traduce comunque l'ultima versione.
    """
    from traduzione.traducibili import e_traducibile, etichetta

    if not accesa() or getattr(oggetto, 'pk', None) is None:
        return
    if not e_traducibile(oggetto):
        return
    # Una bozza non la legge nessuno: tradurla sarebbe spesa per un testo che
    # forse non vedra' mai la luce.
    if getattr(oggetto, 'is_published', True) is False:
        return

    chiave = (etichetta(type(oggetto)), str(oggetto.pk))
    transaction.on_commit(lambda: _metti(chiave))


def _metti(chiave: Chiave) -> None:
    with _guardia:
        if chiave in _in_attesa:
            return
        _in_attesa.add(chiave)
    _coda.put(chiave)


def recupera() -> None:
    """Chiede un ripasso di tutto cio' che non ha ancora tutte le lingue.

    Due momenti la chiamano. L'avvio del server, per ripescare cio' che era in
    coda quando il processo e' morto. E l'aggiunta di una lingua dal pannello:
    li' non si salva nessun contenuto, quindi nessun salvataggio fa da
    innesco, e senza questo la lingua nuova resterebbe vuota fino al riavvio
    successivo — mentre la promessa e' che basti una riga, senza deploy.

    Gira dentro il lavoratore come un compito qualunque: non si somma alle
    traduzioni normali, si mette in fila con loro.
    """
    if accesa():
        _metti(RECUPERO)


def _lavora() -> None:
    while True:
        chiave = _coda.get()
        # Tolto dall'attesa **prima** di lavorarci, non dopo: se qualcuno
        # salva di nuovo lo stesso oggetto mentre lo stiamo traducendo, quella
        # modifica deve poter rientrare in coda. Altrimenti resterebbe fuori
        # proprio nel momento in cui e' piu' probabile che arrivi.
        with _guardia:
            _in_attesa.discard(chiave)
        try:
            close_old_connections()
            if chiave == RECUPERO:
                _recupera()
            else:
                _traduci(chiave)
        except Exception:
            logger.exception('Traduzione in sottofondo non riuscita: %s', chiave)
        finally:
            close_old_connections()
            _coda.task_done()


def _traduci(chiave: Chiave) -> None:
    from django.apps import apps

    from traduzione.servizio import traduci_tutto

    app_label, nome = chiave[0].split('.')
    modello = apps.get_model(app_label, nome)
    # Riletto adesso, non com'era al salvataggio: fra l'uno e l'altro possono
    # esserci altre modifiche, e si traduce l'ultima versione.
    oggetto = modello.objects.filter(pk=chiave[1]).first()
    if oggetto is None:
        return  # cancellato nel frattempo
    traduci_tutto(oggetto)


def _recupera() -> None:
    """Traduce cio' che non ha ancora tutte le lingue, saltando se lo fa gia' un altro."""
    from traduzione import lucchetto
    from traduzione.arretrati import traduci_arretrati

    with lucchetto.preso() as nostro:
        if not nostro:
            logger.info('Arretrati: li sta gia recuperando un altro processo.')
            return
        fatte = traduci_arretrati()
    if fatte:
        logger.info('Arretrati recuperati: %s', fatte)
