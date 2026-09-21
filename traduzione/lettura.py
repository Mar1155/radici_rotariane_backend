"""Servire un contenuto nella lingua del lettore.

Una regola sola, applicata da tutte le API: se esiste una traduzione nella
lingua richiesta la si serve, altrimenti l'originale; e in entrambi i casi si
dice **in che lingua e' stato scritto**, cosi' il frontend puo' offrire "vedi
nella lingua originale".

Sta qui e non dentro ogni serializer perche' e' la stessa domanda ovunque, e
tre copie della stessa regola prima o poi divergono. Per la stessa ragione i
campi tradotti **non si dichiarano piu' qui**: li dichiara `traducibili.py`, e
averne due elenchi era gia' costato — i `campi_tradotti` dei serializer e le
colonne `translated_*` delle tabelle dicevano cose leggermente diverse.

La sostituzione avviene in `to_representation`, non dichiarando campi di sola
lettura: gli stessi serializer servono anche a **scrivere** un messaggio o un
commento, e un campo calcolato non si puo' scrivere.
"""

from __future__ import annotations

from django.db.models import Prefetch

from traduzione.percorsi import applica
from traduzione.servizio import lingua_di_stesura, traduzione_di


def lingua_di(request) -> str | None:
    """La lingua chiesta da chi sta leggendo, se e' una che serviamo."""
    from traduzione import lingue
    return lingue.normalizza(request.GET.get('locale') if request else None)


def con_traduzioni(qs, lingua: str | None, dentro: str | None = None):
    """Il queryset con le traduzioni nella lingua richiesta gia' caricate.

    Senza, ogni oggetto di una lista fa una query per conto suo. Chi dimentica
    di chiamarlo ottiene il comportamento di prima, non un errore: e' una
    misura di velocita', non di correttezza.

    `dentro` serve quando il queryset non e' fatto degli oggetti da tradurre ma
    di righe che li contengono — i salvataggi, per esempio, che portano la card.
    """
    if not lingua:
        return qs
    from traduzione.models import Traduzione
    percorso = f'{dentro}__traduzioni' if dentro else 'traduzioni'
    return qs.prefetch_related(Prefetch(
        percorso,
        queryset=Traduzione.objects.filter(target_language=lingua),
        to_attr='_traduzioni_lingua'))


class InLinguaDelLettore:
    """Mixin per i serializer dei contenuti tradotti."""

    def lingua_richiesta(self):
        richiesta = self.context.get('locale')
        if not richiesta:
            req = self.context.get('request')
            richiesta = req.GET.get('locale') if req else None
        return (richiesta or '').strip().lower() or None

    def to_representation(self, obj):
        dati = super().to_representation(obj)
        lingua = self.lingua_richiesta()
        origine = lingua_di_stesura(obj)

        if not lingua or lingua == origine:
            dati['translated_from'] = None
            return dati

        traduzione = traduzione_di(obj, lingua)
        if traduzione is None:
            dati['translated_from'] = None
            return dati

        # `solo=set(dati)` non ricostruisce cio' che il serializer non emette:
        # in una lista di articoli il corpo non si manda, e rifarlo sarebbe
        # lavoro buttato su ogni riga.
        for campo, valore in applica(obj, traduzione.texts, solo=set(dati)).items():
            if valore:
                dati[campo] = valore

        # E' cosi' che il lettore sa di stare leggendo una traduzione, e che il
        # frontend puo' offrirgli l'originale.
        dati['translated_from'] = origine
        return dati
