"""Servire un contenuto nella lingua del lettore.

Una regola sola, applicata da tutte le API: se esiste una traduzione nella
lingua richiesta la si serve, altrimenti l'originale; e in entrambi i casi si
dice **in che lingua e' stato scritto**, cosi' il frontend puo' offrire "vedi
nella lingua originale".

Sta qui e non dentro ogni serializer perche' e' la stessa domanda ovunque, e
tre copie della stessa regola prima o poi divergono.

La sostituzione avviene in `to_representation`, non dichiarando campi di sola
lettura: gli stessi serializer servono anche a **scrivere** un messaggio o un
commento, e un campo calcolato non si puo' scrivere.
"""

from __future__ import annotations


class InLinguaDelLettore:
    """Mixin per i serializer di contenuti scritti da persone.

    Chi lo usa dichiara `campi_tradotti`: campo sull'oggetto -> campo sulla
    traduzione.
    """

    #: {'title': 'translated_title', ...}
    campi_tradotti: dict[str, str] = {}
    #: L'attributo che elenca le traduzioni.
    relazione_traduzioni = 'translations'

    def lingua_richiesta(self):
        richiesta = self.context.get('locale')
        if not richiesta:
            req = self.context.get('request')
            richiesta = req.GET.get('locale') if req else None
        return (richiesta or '').strip().lower() or None

    def traduzione_per(self, obj):
        lingua = self.lingua_richiesta()
        origine = getattr(obj, 'source_locale', 'it') or 'it'
        if not lingua or lingua == origine:
            return None
        return next(
            (t for t in getattr(obj, self.relazione_traduzioni).all()
             if t.target_language == lingua),
            None)

    def to_representation(self, obj):
        dati = super().to_representation(obj)
        traduzione = self.traduzione_per(obj)
        if traduzione is None:
            dati['translated_from'] = None
            return dati

        for campo, campo_tradotto in self.campi_tradotti.items():
            valore = getattr(traduzione, campo_tradotto, '')
            if valore and campo in dati:
                dati[campo] = valore
        # E' cosi' che il lettore sa di stare leggendo una traduzione, e che il
        # frontend puo' offrirgli l'originale.
        dati['translated_from'] = getattr(obj, 'source_locale', 'it') or 'it'
        return dati
