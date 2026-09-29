"""Un solo traduttore alla volta, in tutto il sistema.

Ogni traduzione si paga, e due processi che traducono le stesse cose pagano
due volte lo stesso testo. Succede facilmente: una sessione che cade a meta'
invita a rilanciare il comando mentre il primo giro e' ancora vivo, e un
riavvio del server fa ripartire il recupero degli arretrati mentre un'altra
istanza lo sta gia' facendo.

Un lucchetto consultivo di PostgreSQL e non una riga di tabella, perche' si
libera da solo quando il processo muore — anche se muore male. Un lucchetto
scritto da qualche parte, dopo un processo ucciso, resterebbe appeso a bloccare
tutti, e ci vorrebbe una persona per toglierlo.

Non protegge la singola scrittura: quella e' gia' al sicuro da sola
(`servizio.traduci` usa `get_or_create`). Protegge la **spesa**.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager

from django.db import connection

logger = logging.getLogger(__name__)

# Un numero qualunque, purche' sempre lo stesso: e' il nome del lucchetto.
CHIAVE = 8314159


def prendi() -> bool:
    """Vero se da adesso siamo noi a tradurre. Falso se lo sta gia' facendo un altro."""
    if connection.vendor != 'postgresql':
        return True
    with connection.cursor() as cursore:
        cursore.execute('SELECT pg_try_advisory_lock(%s)', [CHIAVE])
        return bool(cursore.fetchone()[0])


def lascia() -> None:
    if connection.vendor != 'postgresql':
        return
    with connection.cursor() as cursore:
        cursore.execute('SELECT pg_advisory_unlock(%s)', [CHIAVE])


@contextmanager
def preso():
    """Esegue il blocco solo se il lucchetto e' libero; altrimenti restituisce False.

        with preso() as nostro:
            if not nostro:
                return
            ...
    """
    nostro = prendi()
    try:
        yield nostro
    finally:
        if nostro:
            lascia()
