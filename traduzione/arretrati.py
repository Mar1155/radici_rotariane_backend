"""Tradurre tutto cio' che non ha ancora tutte le lingue.

Due posti lo chiedono, e devono fare la stessa cosa: il comando
`translate_pending`, che una persona lancia, e il recupero all'avvio del
server, che nessuno lancia. Quest'ultimo esiste perche' la traduzione al
salvataggio vive nella memoria del processo: se il processo muore mentre sta
lavorando — un deploy, un riavvio — quel pezzo si perderebbe per sempre, e il
lettore straniero resterebbe con una pagina in italiano senza che nessuno se
ne accorga.

Costa poco quando non c'e' niente da fare: confronta le impronte e passa
oltre, senza chiamare il motore. Se non e' cambiato niente, non si paga niente.
"""

from __future__ import annotations

import logging

from traduzione import lingue
from traduzione.motori import MotoreTraduzione, motore
from traduzione.percorsi import estrai
from traduzione.servizio import e_allineata, lingua_di_stesura, traduci, traduzione_di
from traduzione.traducibili import etichetta, modelli

logger = logging.getLogger(__name__)


def traduci_arretrati(m: MotoreTraduzione | None = None, *, lingua: str | None = None,
                      forza: bool = False, limite: int = 0,
                      da_fare: list | None = None,
                      su_errore=None) -> dict[str, int]:
    """Quante traduzioni ha fatto, per modello.

    `su_errore(etichetta, pk, lingua, errore)` viene chiamata per ogni oggetto
    che fallisce, e il giro continua: un articolo che il motore non digerisce
    non deve fermare gli altri settecento.
    """
    m = m or motore()
    su_errore = su_errore or (lambda modello, pk, lingua, errore: logger.warning(
        'Traduzione non riuscita: %s #%s -> %s: %s', modello, pk, lingua, errore))

    fatte: dict[str, int] = {}
    for modello in (da_fare if da_fare is not None else modelli()):
        n = _per_modello(modello, m, lingua, forza, limite, su_errore)
        if n:
            fatte[etichetta(modello)] = n
    return fatte


def _per_modello(modello, m, lingua, forza, limite, su_errore) -> int:
    qs = modello.objects.all().order_by('pk')
    # Gli articoli non pubblicati non si servono a nessuno: tradurli sarebbe
    # spesa per un testo che forse non vedra' mai la luce.
    if hasattr(modello, 'is_published'):
        qs = qs.filter(is_published=True)
    qs = qs.prefetch_related('traduzioni')
    if limite:
        qs = qs[:limite]

    fatte = 0
    for oggetto in qs:
        origine = lingua_di_stesura(oggetto)
        bersagli = [lingua] if lingua else lingue.altre_lingue(origine)
        for verso in bersagli:
            if verso == origine:
                continue
            try:
                prima = traduzione_di(oggetto, verso)
                if (prima is not None and not forza
                        and e_allineata(prima, estrai(oggetto), m, origine)):
                    continue
                if traduci(oggetto, verso, m, forza=forza):
                    fatte += 1
            except Exception as errore:
                su_errore(etichetta(modello), oggetto.pk, verso, errore)
    return fatte
