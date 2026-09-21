"""Quello che si puo' sbagliare dichiarando cosa e' traducibile.

Tutti e tre i controlli qui rispondono alla stessa esigenza: un errore in
`traducibili.py` non si vede come un errore, si vede come **testo che resta in
italiano**. E il testo che resta in italiano assomiglia molto a una traduzione
non ancora fatta, quindi nessuno lo segnala.

Si vedono a `manage.py check`, cioe' al deploy. Precedente nel progetto:
`common/checks.py`.
"""

from django.core.checks import Error, Warning, register


@register('traduzione')
def controlla_campi_dichiarati(app_configs, **kwargs):
    """Ogni campo dichiarato deve esistere sul modello."""
    from traduzione.traducibili import TRADUCIBILI
    from django.apps import apps

    problemi = []
    for chiave, campi in TRADUCIBILI.items():
        app_label, nome = chiave.split('.')
        try:
            modello = apps.get_model(app_label, nome)
        except LookupError:
            problemi.append(Error(
                f'`{chiave}` e dichiarato traducibile ma il modello non esiste.',
                hint='Forse e stato rinominato o cancellato.',
                id='traduzione.E001'))
            continue

        esistenti = {f.name for f in modello._meta.get_fields()}
        for campo in campi:
            if campo not in esistenti:
                problemi.append(Error(
                    f'`{chiave}.{campo}` e dichiarato traducibile ma il campo '
                    f'non esiste.',
                    hint='Un campo rinominato lascia la traduzione muta: il '
                         'testo resta nella lingua di partenza e sembra una '
                         'traduzione non ancora fatta.',
                    id='traduzione.E002'))
    return problemi


@register('traduzione')
def controlla_generi(app_configs, **kwargs):
    """Ogni campo deve essere associato a un genere vero."""
    from traduzione.generi import Genere
    from traduzione.traducibili import TRADUCIBILI

    problemi = []
    for chiave, campi in TRADUCIBILI.items():
        for campo, genere in campi.items():
            if not isinstance(genere, Genere):
                problemi.append(Error(
                    f'`{chiave}.{campo}` non dichiara un genere valido.',
                    hint='Usa TESTO, DIZIONARIO, DOCUMENTO, RICCO o FLUSSO.',
                    id='traduzione.E003'))
    return problemi


@register('traduzione')
def controlla_catalogo_blocchi(app_configs, **kwargs):
    """Ogni foglia del catalogo dei blocchi dev'essere classificata.

    Il camminatore dello StreamField decide per classe: o un blocco e' testo da
    tradurre, o e' opaco, o e' un contenitore in cui scendere. Un blocco nuovo
    con un tipo di campo mai visto cadrebbe fuori da tutte e tre, e il suo
    testo non arriverebbe mai al traduttore — in silenzio.

    Qui diventa un errore di deploy.
    """
    from wagtail import blocks
    from traduzione.flusso import classifica

    try:
        from cms.blocks import PageBodyBlock
        catalogo = PageBodyBlock()
    except Exception as exc:
        return [Warning(f'Catalogo dei blocchi non ispezionabile: {exc}',
                        id='traduzione.W004')]

    ignoti = []

    def cammina(blocco, percorso):
        genere = classifica(blocco)
        if genere == 'ignoto':
            ignoti.append((' > '.join(percorso), type(blocco).__name__))
            return
        if genere != 'contenitore':
            return
        if isinstance(blocco, blocks.ListBlock):
            cammina(blocco.child_block, percorso + ['[]'])
        else:
            for nome, figlio in blocco.child_blocks.items():
                cammina(figlio, percorso + [nome])

    cammina(catalogo, ['contenuto'])

    return [Error(
        f'Il blocco `{dove}` ({classe}) non e classificato: il camminatore '
        f'dello StreamField non sa se tradurlo o saltarlo.',
        hint='Aggiungi la sua classe a una delle famiglie in '
             'traduzione/flusso.py:_classi(). Senza, il suo testo non '
             'arrivera mai al traduttore e nessuno se ne accorgera.',
        id='traduzione.E005') for dove, classe in ignoti]
