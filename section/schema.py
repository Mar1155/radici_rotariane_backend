"""Lo schema del corpo di un articolo, e la sua validazione.

Il corpo si salva come documento ProseMirror (JSON), non come HTML. Tre ragioni:

1. **Sicurezza per costruzione.** Un'allowlist su HTML è una lista di cose da
   vietare, e si dimentica sempre qualcosa. Qui vale l'opposto: si costruisce un
   documento nuovo copiando solo i nodi previsti. Ciò che non è previsto non
   viene "ripulito", semplicemente non viene copiato.
2. **Traduzione.** I nodi di testo si estraggono per percorso, si traducono e si
   reinseriscono senza toccare la formattazione. Su HTML significherebbe
   riscrivere il markup, ed è il motivo per cui le traduzioni attuali perdono
   le immagini.
3. **Palette per tipo.** Ogni tipo di articolo dichiara quali blocchi ammette
   (`ArticleType.body_blocks`). Qui si verifica: il frontend nasconde i pulsanti,
   ma è il server a decidere.
"""

from __future__ import annotations

import re

# --- Da chiave di palette ai nodi che abilita ---------------------------------
# Le chiavi sono quelle di `cms.vocabularies.BODY_BLOCK_CHOICES`.
NODI_PER_BLOCCO = {
    'paragraph': {'paragraph', 'hardBreak'},
    'heading': {'heading'},
    'image': {'image'},
    'gallery': {'gallery'},
    'quote': {'blockquote'},
    'list': {'bulletList', 'orderedList', 'listItem'},
    'embed': {'embed'},
}

# Il paragrafo c'e' sempre: senza, un documento non puo' contenere testo e
# l'editor non avrebbe dove scrivere.
NODI_SEMPRE = {'doc', 'paragraph', 'text', 'hardBreak'}

# La formattazione non e' un blocco: non si configura per tipo di articolo.
MARK_AMMESSI = {'bold', 'italic', 'underline', 'strike', 'code', 'link'}

LIVELLI_TITOLO = (2, 3, 4)   # h1 e' il titolo dell'articolo, non del corpo

# Un indirizzo dentro un link: solo http(s) e mailto. Niente `javascript:`,
# niente `data:`.
SCHEMI_LINK = re.compile(r'^(https?://|mailto:)', re.IGNORECASE)

# Quanto in profondita' puo' annidarsi un documento. Serve contro i documenti
# costruiti a mano per far esplodere il parser, non contro gli autori.
PROFONDITA_MASSIMA = 12


class CorpoNonValido(ValueError):
    """Il documento non è un corpo di articolo trattabile."""


def nodi_ammessi(blocchi) -> set[str]:
    """I tipi di nodo che questa palette abilita."""
    ammessi = set(NODI_SEMPRE)
    for chiave in (blocchi or []):
        ammessi |= NODI_PER_BLOCCO.get(chiave, set())
    return ammessi


def _testo(valore) -> str:
    return valore if isinstance(valore, str) else ''


def _pulisci_marks(marks, ammessi):
    risultato = []
    for m in marks if isinstance(marks, list) else []:
        if not isinstance(m, dict):
            continue
        tipo = m.get('type')
        if tipo not in ammessi:
            continue
        if tipo == 'link':
            href = _testo((m.get('attrs') or {}).get('href'))
            if not SCHEMI_LINK.match(href):
                continue      # il link cade, il testo resta
            risultato.append({'type': 'link', 'attrs': {'href': href}})
        else:
            risultato.append({'type': tipo})
    return risultato


def _pulisci_nodo(nodo, ammessi, profondita):
    """Ricostruisce un nodo copiandone solo ciò che è previsto. None se cade."""
    if not isinstance(nodo, dict) or profondita > PROFONDITA_MASSIMA:
        return None
    tipo = nodo.get('type')
    if tipo not in ammessi:
        return None

    if tipo == 'text':
        testo = _testo(nodo.get('text'))
        if not testo:
            return None
        pulito = {'type': 'text', 'text': testo}
        marks = _pulisci_marks(nodo.get('marks'), MARK_AMMESSI)
        if marks:
            pulito['marks'] = marks
        return pulito

    if tipo == 'hardBreak':
        return {'type': 'hardBreak'}

    if tipo == 'image':
        asset = nodo.get('attrs', {}).get('assetId')
        if not isinstance(asset, int):
            return None       # un'immagine senza riferimento non e' un'immagine
        attrs = {'assetId': asset}
        alt = _testo(nodo.get('attrs', {}).get('alt')).strip()
        if alt:
            attrs['alt'] = alt[:255]
        return {'type': 'image', 'attrs': attrs}

    if tipo == 'gallery':
        ids = nodo.get('attrs', {}).get('assetIds')
        ids = [i for i in ids if isinstance(i, int)] if isinstance(ids, list) else []
        if not ids:
            return None
        return {'type': 'gallery', 'attrs': {'assetIds': ids[:24]}}

    if tipo == 'embed':
        url = _testo(nodo.get('attrs', {}).get('url'))
        if not SCHEMI_LINK.match(url):
            return None
        return {'type': 'embed', 'attrs': {'url': url}}

    # Nodi contenitori: doc, paragraph, heading, blockquote, liste.
    pulito = {'type': tipo}
    if tipo == 'heading':
        livello = nodo.get('attrs', {}).get('level')
        pulito['attrs'] = {
            'level': livello if livello in LIVELLI_TITOLO else LIVELLI_TITOLO[0]}

    figli = []
    for figlio in nodo.get('content') or []:
        ripulito = _pulisci_nodo(figlio, ammessi, profondita + 1)
        if ripulito is not None:
            figli.append(ripulito)

    # Un paragrafo vuoto e' una riga vuota voluta: si tiene. Un titolo o una
    # citazione senza testo no, sono residui di una cancellazione.
    if not figli and tipo not in ('paragraph', 'doc'):
        return None
    if figli:
        pulito['content'] = figli
    return pulito


def pulisci_corpo(documento, blocchi=None):
    """Il documento ripulito, contenente solo ciò che la palette ammette.

    Accetta `None` e documenti vuoti: un articolo può non avere corpo.
    """
    if documento in (None, '', {}):
        return None
    if not isinstance(documento, dict) or documento.get('type') != 'doc':
        raise CorpoNonValido('Il corpo deve essere un documento ProseMirror.')

    pulito = _pulisci_nodo(documento, nodi_ammessi(blocchi), 0)
    if not pulito or not pulito.get('content'):
        return None
    return pulito


def testo_semplice(documento) -> str:
    """Il solo testo, per ricerca e traduzione."""
    if not isinstance(documento, dict):
        return ''
    pezzi = []

    def visita(nodo):
        if not isinstance(nodo, dict):
            return
        if nodo.get('type') == 'text':
            pezzi.append(_testo(nodo.get('text')))
        for figlio in nodo.get('content') or []:
            visita(figlio)
        # Un blocco chiuso e' una interruzione di riga, non un attacco di parola.
        if nodo.get('type') in ('paragraph', 'heading', 'blockquote', 'listItem'):
            pezzi.append('\n')

    visita(documento)
    return re.sub(r'\n{3,}', '\n\n', ''.join(pezzi)).strip()

# --- Testo per la traduzione --------------------------------------------------
#
# Il documento si traduce **nodo per nodo**, non riscrivendo il markup: si
# estraggono i testi col loro percorso, si traducono, si rimettono dove stavano.
# La formattazione non passa mai dal traduttore, quindi non puo' corrompersi —
# ed e' il motivo per cui il corpo e' un documento e non HTML.


def _percorsi_testo(nodo, percorso=()):
    """Coppie (percorso, testo) per ogni nodo di testo del documento."""
    if not isinstance(nodo, dict):
        return
    if nodo.get('type') == 'text' and _testo(nodo.get('text')):
        yield percorso, nodo['text']
    # Anche le didascalie delle immagini sono testo da tradurre.
    if nodo.get('type') == 'image' and _testo((nodo.get('attrs') or {}).get('alt')):
        yield percorso + ('alt',), nodo['attrs']['alt']
    for i, figlio in enumerate(nodo.get('content') or []):
        yield from _percorsi_testo(figlio, percorso + (i,))


def estrai_testi(documento) -> dict[str, str]:
    """I testi del documento, indicizzati per percorso.

    La chiave e' il percorso reso stringa, cosi' sopravvive a un giro in JSON:
    un traduttore che restituisce le stesse chiavi permette di verificare che
    non ne abbia inventate o perse.
    """
    if not isinstance(documento, dict):
        return {}
    return {'.'.join(str(p) for p in percorso): testo
            for percorso, testo in _percorsi_testo(documento)}


def _scrivi(nodo, passi, valore):
    if not passi:
        return
    if passi[0] == 'alt':
        nodo.setdefault('attrs', {})['alt'] = valore
        return
    if len(passi) == 1:
        figli = nodo.get('content') or []
        indice = passi[0]
        if isinstance(indice, int) and 0 <= indice < len(figli):
            if figli[indice].get('type') == 'text':
                figli[indice]['text'] = valore
        return
    figli = nodo.get('content') or []
    indice = passi[0]
    if isinstance(indice, int) and 0 <= indice < len(figli):
        _scrivi(figli[indice], passi[1:], valore)


def reinserisci_testi(documento, testi: dict[str, str]):
    """Il documento con i testi sostituiti ai loro percorsi.

    Non modifica l'originale. Un percorso che non esiste piu' viene ignorato:
    il documento puo' essere cambiato mentre la traduzione era in corso, e in
    quel caso si perde una frase, non l'articolo.
    """
    import copy

    if not isinstance(documento, dict):
        return documento
    copia = copy.deepcopy(documento)
    for chiave, valore in (testi or {}).items():
        passi = [p if p == 'alt' else int(p)
                 for p in chiave.split('.') if p != '']
        _scrivi(copia, passi, valore)
    return copia
