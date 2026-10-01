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


def scelte() -> list[tuple[str, str]]:
    """Le lingue in cui si puo' dichiarare di aver scritto qualcosa.

    Callable e non lista: Django 5 la rivaluta a ogni form, quindi una lingua
    aggiunta da /cms/ compare subito nella tendina senza una migrazione. Con una
    lista fissa, aggiungere una lingua dal pannello avrebbe lasciato fuori
    proprio il campo che serve a dire in che lingua si sta scrivendo.

    **Tutte** le registrate, anche quelle spente, e in ogni caso la lingua del
    sito. Due ragioni, entrambe imparate rompendo qualcosa: `choices` non decide
    solo cosa mostrare, decide anche cosa il database accetta — quindi su un
    database appena migrato, senza righe, nemmeno l'italiano era un valore
    valido e **non si poteva creare una pagina**. E spegnere una lingua serve a
    toglierla dal selettore dei lettori, non a rendere impossibile salvare le
    pagine che qualcuno aveva scritto in quella lingua.
    """
    from django.conf import settings
    from traduzione.models import Lingua
    predefinita = settings.LANGUAGE_CODE.split('-')[0]
    try:
        righe = [(l.codice, l.nome) for l in Lingua.objects.order_by('ordine', 'codice')]
    except Exception:
        # La tabella non c'e' ancora (prima migrate): non e' un errore.
        righe = []
    if predefinita not in {c for c, _ in righe}:
        righe.insert(0, (predefinita, predefinita))
    return righe


def dalla_richiesta(request) -> str | None:
    """La lingua in cui chi sta leggendo vuole il contenuto. Un posto solo.

    Due modi, in ordine. Il parametro `?locale=` vince, perche' e' esplicito:
    un collegamento condiviso porta con se' la lingua in cui e' stato letto.
    Altrimenti l'intestazione `Accept-Language`, che il frontend mette su
    **ogni** richiesta.

    L'intestazione e' stata aggiunta dopo un guasto che vale la pena ricordare:
    con il solo `?locale=`, ogni servizio del frontend doveva ricordarsi di
    aggiungerlo, e due su quattro non lo facevano. Forum e chat si servivano
    sempre in italiano — non perche' le traduzioni mancassero, ma perche'
    nessuno le chiedeva. Una cosa che ogni chiamante deve ricordare e' una cosa
    che qualche chiamante dimentica.
    """
    if request is None:
        return None
    esplicita = normalizza(request.GET.get('locale'))
    if esplicita:
        return esplicita
    return dall_intestazione(request.META.get('HTTP_ACCEPT_LANGUAGE'))


def dall_intestazione(valore: str | None) -> str | None:
    """La prima lingua di `Accept-Language` che serviamo.

    Formato: `en-GB,en;q=0.9,it;q=0.8`. Si guardano in ordine di preferenza e
    si prende la prima che e' attiva, cosi' un browser che chiede una lingua
    che non abbiamo ricade su quella dopo invece che sull'originale.
    """
    if not valore:
        return None
    pezzi = []
    for parte in valore.split(','):
        codice, _, resto = parte.strip().partition(';')
        peso = 1.0
        if resto.startswith('q='):
            try:
                peso = float(resto[2:])
            except ValueError:
                peso = 0.0
        pezzi.append((peso, codice))
    for _, codice in sorted(pezzi, key=lambda x: -x[0]):
        if codice.strip() == '*':
            continue
        scelta = normalizza(codice)
        if scelta:
            return scelta
    return None


def svuota_cache(**kwargs):
    global _cache
    _cache = None


def _collega():
    from traduzione.models import Lingua
    post_save.connect(svuota_cache, sender=Lingua, dispatch_uid='lingue-salva')
    post_delete.connect(svuota_cache, sender=Lingua, dispatch_uid='lingue-cancella')
