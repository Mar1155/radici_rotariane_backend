"""Quali lingue sono attive, senza chiederlo al database ogni volta.

La domanda "in che lingue si traduce" si pone a ogni articolo, a ogni post e a
ogni richiesta dell'API: farne una query ogni volta sarebbe una query per
niente, perche' la risposta cambia quando qualcuno aggiunge una lingua, cioe'
qualche volta all'anno.

La cache e' di processo e si svuota da sola quando la tabella cambia, con lo
stesso schema che `cms/signals.py` usa per la cache del frontend.
"""

from django.db.models.signals import post_delete, post_save

_cache: list[str] | None = None


def codici_attivi() -> list[str]:
    """I codici delle lingue attive, in ordine.

    Su un database vuoto — durante la prima migrate, o in un test che non ha
    seminato niente — non ce n'e' nessuna: si ripiega sulla lingua di stesura,
    cosi' il sito funziona invece di sollevare.
    """
    global _cache
    if _cache is None:
        from django.conf import settings
        from traduzione.models import Lingua
        try:
            _cache = list(
                Lingua.objects.filter(attiva=True)
                .order_by('ordine', 'codice')
                .values_list('codice', flat=True))
        except Exception:
            # La tabella non c'e' ancora (prima migrate): non e' un errore.
            return [settings.LANGUAGE_CODE]
        if not _cache:
            _cache = [settings.LANGUAGE_CODE]
    return list(_cache)


def altre_lingue(origine: str | None) -> list[str]:
    """Le lingue in cui tradurre cio' che e' stato scritto in `origine`."""
    from django.conf import settings
    sorgente = (origine or settings.LANGUAGE_CODE or 'it').lower()
    return [c for c in codici_attivi() if c != sorgente]


def e_attiva(codice: str | None) -> bool:
    return bool(codice) and codice.lower() in codici_attivi()


def normalizza(richiesta: str | None) -> str | None:
    """Il codice di lingua chiesto, se e' una lingua che serviamo.

    Accetta anche `en-GB` e simili: la variante regionale non ci interessa,
    interessa la lingua.
    """
    codice = (richiesta or '').strip().lower().split('-')[0]
    return codice if e_attiva(codice) else None


def svuota_cache(**kwargs):
    global _cache
    _cache = None


def _collega():
    from traduzione.models import Lingua
    post_save.connect(svuota_cache, sender=Lingua, dispatch_uid='lingue-salva')
    post_delete.connect(svuota_cache, sender=Lingua, dispatch_uid='lingue-cancella')
