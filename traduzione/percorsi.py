"""Estrarre i testi di un oggetto e rimetterceli tradotti.

Due funzioni sole, che valgono per qualunque cosa sia dichiarata in
`traducibili.py`: un articolo, un commento, una pagina del CMS, l'etichetta di
un tag.

    estrai(oggetto)                  -> {percorso: testo}
    applica(oggetto, testi, solo=…)  -> {campo: valore con i testi dentro}

**La grammatica del percorso, in una riga:** il primo `:` separa il campo dal
percorso interno, e dentro i passi sono separati da `.`. Nessuna chiave in
gioco contiene `:` — sono slug, UUID o indici — quindi la divisione non e'
ambigua.

    title                                  un campo semplice
    info_values:giorni                     una chiave di un dizionario
    body:0.1                               un nodo di un documento ProseMirror
    body:2a96a0d2-….title                  un campo dentro un blocco StreamField
    content_html:1.0                       un nodo di testo dentro dell'HTML
"""

from __future__ import annotations

from traduzione.traducibili import campi_di

SEPARATORE = ':'


def estrai(oggetto) -> dict[str, str]:
    """I testi traducibili dell'oggetto, indicizzati per percorso."""
    testi: dict[str, str] = {}
    for campo, genere in campi_di(oggetto).items():
        valore = getattr(oggetto, campo, None)
        for interno, testo in genere.estrai(valore).items():
            chiave = f'{campo}{SEPARATORE}{interno}' if interno else campo
            testi[chiave] = testo
    return testi


def applica(oggetto, testi: dict[str, str],
            solo: set[str] | None = None) -> dict[str, object]:
    """I valori dei campi con i testi tradotti al loro posto.

    **Non tocca l'oggetto**: restituisce valori nuovi, che il chiamante mette
    dove servono. Cosi' la stessa istanza puo' essere servita in due lingue
    nella stessa richiesta senza sporcarsi.

    `solo` limita il lavoro ai campi che il chiamante usera' davvero: in una
    lista di articoli il corpo non si emette, e ricostruirlo sarebbe lavoro
    buttato. Un percorso senza traduzione **ricade sull'originale**, che e' il
    motivo per cui un paragrafo appena aggiunto compare in italiano dentro una
    pagina inglese invece di sparire.
    """
    dichiarati = campi_di(oggetto)
    se_ne_occupa = {c: {} for c in dichiarati}

    for chiave, testo in (testi or {}).items():
        campo, _, interno = chiave.partition(SEPARATORE)
        if campo in se_ne_occupa:
            se_ne_occupa[campo][interno] = testo

    risultato: dict[str, object] = {}
    for campo, genere in dichiarati.items():
        if solo is not None and campo not in solo:
            continue
        tradotti = se_ne_occupa[campo]
        if not tradotti:
            continue
        valore = getattr(oggetto, campo, None)
        if valore is None:
            continue
        risultato[campo] = genere.reinserisci(valore, tradotti)
    return risultato


def percorsi_mancanti(oggetto, testi: dict[str, str]) -> dict[str, str]:
    """I testi dell'originale che la traduzione non copre ancora.

    E' cio' che si manda al motore in una ritraduzione: il resto e' gia' fatto,
    o e' stato corretto a mano e non si tocca.
    """
    sorgente = estrai(oggetto)
    return {k: v for k, v in sorgente.items() if k not in (testi or {})}
