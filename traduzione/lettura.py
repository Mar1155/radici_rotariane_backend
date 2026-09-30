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
    return lingue.dalla_richiesta(request)


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
        """La stessa domanda di `lingua_di`, e la stessa risposta.

        Aveva una copia sua, che leggeva solo `?locale=` e non normalizzava: due
        punti che rispondevano quasi alla stessa cosa, ed e' il genere di
        "quasi" che si scopre in produzione.
        """
        from traduzione import lingue
        esplicita = self.context.get('locale')
        if esplicita:
            return lingue.normalizza(esplicita)
        return lingue.dalla_richiesta(self.context.get('request'))

    def to_representation(self, obj):
        dati = super().to_representation(obj)
        lingua = self.lingua_richiesta()
        origine = lingua_di_stesura(obj)

        if not lingua or lingua == origine:
            return self._originale(dati)

        traduzione = traduzione_di(obj, lingua)
        if traduzione is None:
            return self._originale(dati)

        # `solo=set(dati)` non ricostruisce cio' che il serializer non emette:
        # in una lista di articoli il corpo non si manda, e rifarlo sarebbe
        # lavoro buttato su ogni riga.
        sostituiti = {}
        for campo, valore in applica(obj, traduzione.texts, solo=set(dati)).items():
            if valore:
                sostituiti[campo] = dati[campo]
                dati[campo] = valore

        if not sostituiti:
            return self._originale(dati)

        # E' cosi' che il lettore sa di stare leggendo una traduzione.
        dati['translated_from'] = origine
        # E questo e' cio' che gli permette di tornare all'originale **subito**,
        # senza una seconda richiesta. Prima il frontend rileggeva l'oggetto
        # omettendo la lingua; da quando la lingua viaggia nell'intestazione
        # quel modo non funziona piu' — l'intestazione la dice comunque — e
        # "Vedi originale" avrebbe ricaricato la stessa traduzione. Portarsi
        # dietro le due versioni e' anche piu' semplice di due richieste: nella
        # chat, dove ogni messaggio ha il suo pulsante, l'alternativa era una
        # richiesta per messaggio.
        dati['originale'] = sostituiti
        return dati

    @staticmethod
    def _originale(dati):
        """La risposta quando non si traduce: la forma non cambia mai.

        `translated_from` e `originale` ci sono sempre, a `None`: un campo che
        a volte c'e' e a volte no costringe ogni chiamante a difendersi.
        """
        dati['translated_from'] = None
        dati['originale'] = None
        return dati
