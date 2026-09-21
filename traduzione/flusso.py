"""Camminare uno StreamField per trovarci dentro il testo.

Si cammina sui **dati grezzi** — la lista di `{type, value, id}` che sta nel
database — in parallelo alla definizione dei blocchi, non sugli oggetti
`StreamValue`. Cosi' si sa sempre che tipo di blocco si sta guardando, e quindi
se il suo contenuto e' testo da tradurre o un indirizzo da lasciare stare.

**I passi del percorso sono gli id dei blocchi, non gli indici.** Wagtail
assegna un UUID a ogni blocco quando salva, quindi riordinare i blocchi dal
pannello non sposta le traduzioni. In cambio, un comando che ricostruisce il
corpo da zero (`build_pages_sezioni`, `build_page_home`) genera id nuovi e le
invalida tutte: e' il motivo per cui le pagine nuove si scrivono nei JSON di
`cms/contenuti/`, dove gli id sono versionati.

**Cosa si traduce si decide per classe di blocco, non per nome.** Aggiungere il
blocco numero venti domani non richiede di ricordarsi di aggiornare un secondo
elenco; e se il blocco nuovo usa un tipo di campo mai visto, il controllo di
sistema in `traduzione/checks.py` lo segnala al deploy invece di lasciare un
buco di testo non tradotto.
"""

from __future__ import annotations

import copy

from wagtail import blocks


def _classi():
    """Le tre famiglie, risolte una volta sola."""
    from wagtail.blocks.field_block import BaseChoiceBlock

    testuali = (blocks.CharBlock, blocks.TextBlock, blocks.RichTextBlock)
    # L'ordine conta, e va guardato prima questo: `ChoiceBlock` eredita da
    # `CharBlock` (le sue scelte sono chiavi, non testo) e `RawHTMLBlock` da
    # `TextBlock` (e' markup, non prosa). `URLBlock` ed `EmailBlock` invece non
    # ereditano da `CharBlock`, ma elencarli non costa e dice l'intenzione.
    from cms.blocks.common import IdentificatoreBlock

    opachi = (IdentificatoreBlock,
              BaseChoiceBlock, blocks.RawHTMLBlock, blocks.StaticBlock,
              blocks.URLBlock, blocks.EmailBlock, blocks.BooleanBlock,
              blocks.IntegerBlock, blocks.FloatBlock, blocks.DecimalBlock,
              blocks.DateBlock, blocks.TimeBlock, blocks.DateTimeBlock,
              blocks.ChooserBlock)
    contenitori = (blocks.StreamBlock, blocks.StructBlock, blocks.ListBlock)
    return testuali, opachi, contenitori


def classifica(blocco) -> str:
    """'testo', 'opaco', 'contenitore' — o 'ignoto', che e' un errore."""
    testuali, opachi, contenitori = _classi()
    if isinstance(blocco, contenitori):
        return 'contenitore'
    if isinstance(blocco, opachi):
        return 'opaco'
    if isinstance(blocco, testuali):
        return 'testo'
    return 'ignoto'


def _e_ricco(blocco) -> bool:
    return isinstance(blocco, blocks.RichTextBlock)


def _cammina(grezzo, definizione, prefisso: list[str]):
    """Genera `(percorso, testo, e_ricco)` per ogni foglia testuale."""
    genere = classifica(definizione)

    if genere == 'testo':
        if isinstance(grezzo, str) and grezzo.strip():
            yield '.'.join(prefisso), grezzo, _e_ricco(definizione)
        return

    if genere != 'contenitore':
        return

    if isinstance(definizione, blocks.StreamBlock):
        for voce in grezzo or []:
            if not isinstance(voce, dict):
                continue
            figlio = definizione.child_blocks.get(voce.get('type'))
            if figlio is None:
                continue     # blocco deprecato: si salta, come fa il frontend
            passo = str(voce.get('id') or '')
            yield from _cammina(voce.get('value'), figlio, prefisso + [passo])

    elif isinstance(definizione, blocks.StructBlock):
        if not isinstance(grezzo, dict):
            return
        for nome, figlio in definizione.child_blocks.items():
            if nome in grezzo:
                yield from _cammina(grezzo[nome], figlio, prefisso + [nome])

    elif isinstance(definizione, blocks.ListBlock):
        figlio = definizione.child_block
        for voce in grezzo or []:
            # Forma nuova: {'type':'item','value':…,'id':…}. Forma vecchia: il
            # valore nudo, senza id — li' si usa l'indice, che e' quanto c'e'.
            if isinstance(voce, dict) and 'value' in voce and 'id' in voce:
                yield from _cammina(voce['value'], figlio,
                                    prefisso + [str(voce['id'])])
            else:
                indice = (grezzo or []).index(voce)
                yield from _cammina(voce, figlio, prefisso + [f'#{indice}'])


def estrai_dal_flusso(valore, definizione) -> dict[str, str]:
    """I testi di uno StreamField, indicizzati per percorso."""
    grezzo = _grezzo(valore)
    testi: dict[str, str] = {}
    for percorso, testo, ricco in _cammina(grezzo, definizione, []):
        if ricco:
            from traduzione.generi import RICCO
            for sotto, frammento in RICCO.estrai(testo).items():
                testi[f'{percorso}~{sotto}'] = frammento
        else:
            testi[percorso] = testo.strip()
    return testi


def _grezzo(valore) -> list:
    """I dati grezzi, qualunque forma abbia il valore in arrivo.

    Attenzione a `raw_data`: non e' una lista ma una vista proxy
    (`RawDataView`), quindi un controllo su `isinstance(..., list)` la scarta
    in silenzio e si finisce a camminare su niente.
    """
    if valore is None:
        return []
    if isinstance(valore, (list, tuple)):
        return list(valore)
    grezzo = getattr(valore, 'raw_data', None)
    if grezzo is not None:
        return list(grezzo)
    return list(valore) if hasattr(valore, '__iter__') else []


def _scrivi(grezzo, definizione, prefisso: list[str], testi: dict[str, str]):
    """Sostituisce sul posto, dentro una copia gia' fatta dal chiamante."""
    genere = classifica(definizione)

    if genere == 'testo':
        return      # gestito dal genitore, che sa dove scrivere

    if genere != 'contenitore':
        return

    def valore_per(percorso: list[str], attuale: str, ricco: bool):
        chiave = '.'.join(percorso)
        if ricco:
            frammenti = {k.split('~', 1)[1]: v for k, v in testi.items()
                         if k.startswith(f'{chiave}~')}
            if not frammenti:
                return None
            from traduzione.generi import RICCO
            return RICCO.reinserisci(attuale, frammenti)
        return testi.get(chiave)

    if isinstance(definizione, blocks.StreamBlock):
        for voce in grezzo or []:
            if not isinstance(voce, dict):
                continue
            figlio = definizione.child_blocks.get(voce.get('type'))
            if figlio is None:
                continue
            passo = prefisso + [str(voce.get('id') or '')]
            if classifica(figlio) == 'testo':
                nuovo = valore_per(passo, voce.get('value') or '', _e_ricco(figlio))
                if nuovo:
                    voce['value'] = nuovo
            else:
                _scrivi(voce.get('value'), figlio, passo, testi)

    elif isinstance(definizione, blocks.StructBlock):
        if not isinstance(grezzo, dict):
            return
        for nome, figlio in definizione.child_blocks.items():
            if nome not in grezzo:
                continue
            passo = prefisso + [nome]
            if classifica(figlio) == 'testo':
                nuovo = valore_per(passo, grezzo[nome] or '', _e_ricco(figlio))
                if nuovo:
                    grezzo[nome] = nuovo
            else:
                _scrivi(grezzo[nome], figlio, passo, testi)

    elif isinstance(definizione, blocks.ListBlock):
        figlio = definizione.child_block
        for indice, voce in enumerate(grezzo or []):
            con_id = isinstance(voce, dict) and 'value' in voce and 'id' in voce
            passo = prefisso + [str(voce['id']) if con_id else f'#{indice}']
            if classifica(figlio) == 'testo':
                attuale = voce['value'] if con_id else voce
                nuovo = valore_per(passo, attuale or '', _e_ricco(figlio))
                if nuovo:
                    if con_id:
                        voce['value'] = nuovo
                    else:
                        grezzo[indice] = nuovo
            else:
                _scrivi(voce['value'] if con_id else voce, figlio, passo, testi)


def reinserisci_nel_flusso(valore, testi: dict[str, str], definizione):
    """I dati grezzi dello StreamField con i testi tradotti al loro posto.

    Restituisce **dati grezzi**, non un `StreamValue`: chi legge li rimette in
    forma con `definizione.to_python(...)`, che e' la stessa conversione che
    StreamField fa caricando da database. Reinserire nella rappresentazione API
    non funzionerebbe: `ListBlock.get_api_representation` butta via gli id, e i
    percorsi non coinciderebbero piu'.
    """
    grezzo = copy.deepcopy(_grezzo(valore))
    if testi:
        _scrivi(grezzo, definizione, [], testi)
    return grezzo
