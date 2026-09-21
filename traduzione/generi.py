"""I cinque modi in cui un campo puo' contenere testo.

Un campo non e' sempre una stringa: puo' essere un dizionario a chiavi libere,
un documento ProseMirror, uno StreamField di Wagtail, un frammento di HTML.
Cambia come si trova il testo dentro, non cosa se ne fa: si estrae, si traduce,
si rimette dove stava.

Ogni genere risponde a due domande sole:

    estrai(valore) -> {percorso: testo}
    reinserisci(valore, testi) -> valore nuovo

Il percorso e' una stringa perche' sopravvive a un giro in JSON: il motore
riceve e restituisce le stesse chiavi, e se ne inventa o ne perde si vede.
"""

from __future__ import annotations

import copy


class Genere:
    """Un modo di contenere testo."""

    nome = '?'

    def estrai(self, valore) -> dict[str, str]:
        raise NotImplementedError

    def reinserisci(self, valore, testi: dict[str, str]):
        raise NotImplementedError


class _Testo(Genere):
    """Una stringa: nessun percorso interno."""

    nome = 'testo'

    def estrai(self, valore):
        testo = (valore or '').strip() if isinstance(valore, str) else ''
        return {'': testo} if testo else {}

    def reinserisci(self, valore, testi):
        nuovo = testi.get('')
        return nuovo if nuovo else valore


class _Dizionario(Genere):
    """Un JSON a chiavi libere, come `Card.info_values`.

    Le chiavi sono identificatori (restano), i valori sono testo (si traduce).
    """

    nome = 'dizionario'

    def estrai(self, valore):
        if not isinstance(valore, dict):
            return {}
        return {str(k): str(v).strip()
                for k, v in valore.items() if str(v or '').strip()}

    def reinserisci(self, valore, testi):
        if not isinstance(valore, dict):
            return valore
        copia = dict(valore)
        for chiave, testo in (testi or {}).items():
            if chiave in copia and testo:
                copia[chiave] = testo
        return copia


class _Documento(Genere):
    """Un documento ProseMirror, come `Card.body`.

    Non reinventa niente: `section/schema.py` sa gia' camminarlo, ed e' lo
    stesso codice che valida quello che l'editor manda.
    """

    nome = 'documento'

    def estrai(self, valore):
        from section.schema import estrai_testi
        return estrai_testi(valore)

    def reinserisci(self, valore, testi):
        from section.schema import reinserisci_testi
        return reinserisci_testi(valore, testi)


class _Ricco(Genere):
    """Un frammento di HTML, come `Post.content_html` o un blocco `rich_text`.

    Si estraggono i nodi di testo con il loro percorso di indici e si rimettono
    al loro posto: la formattazione non passa mai dal traduttore, quindi non
    puo' tornare corrotta. E' lo stesso principio del documento ProseMirror,
    su un albero diverso.
    """

    nome = 'ricco'

    def _albero(self, html: str):
        from bs4 import BeautifulSoup
        return BeautifulSoup(html or '', 'html.parser')

    def _nodi(self, albero):
        """I nodi di testo non vuoti, con il loro percorso di indici."""
        from bs4 import NavigableString

        def cammina(nodo, prefisso):
            for i, figlio in enumerate(nodo.children):
                percorso = prefisso + [i]
                if isinstance(figlio, NavigableString):
                    if str(figlio).strip():
                        yield percorso, figlio
                elif hasattr(figlio, 'children'):
                    yield from cammina(figlio, percorso)

        return cammina(albero, [])

    def estrai(self, valore):
        if not isinstance(valore, str) or not valore.strip():
            return {}
        albero = self._albero(valore)
        return {'.'.join(str(p) for p in percorso): str(nodo).strip()
                for percorso, nodo in self._nodi(albero)}

    def reinserisci(self, valore, testi):
        if not isinstance(valore, str) or not valore.strip() or not testi:
            return valore
        albero = self._albero(valore)
        da_mettere = dict(testi)
        for percorso, nodo in list(self._nodi(albero)):
            chiave = '.'.join(str(p) for p in percorso)
            nuovo = da_mettere.get(chiave)
            if nuovo:
                # Si conserva la spaziatura attorno: un testo dentro <b>ciao</b>
                # e uno dentro <p>ciao </p> non si rendono uguali.
                originale = str(nodo)
                prima = originale[:len(originale) - len(originale.lstrip())]
                dopo = originale[len(originale.rstrip()):]
                nodo.replace_with(f'{prima}{nuovo}{dopo}')
        return str(albero)


class _Flusso(Genere):
    """Uno StreamField di Wagtail, come il corpo delle pagine.

    Sta in `traduzione/flusso.py` perche' e' l'unico che ha bisogno di sapere
    com'e' fatto il catalogo dei blocchi.
    """

    nome = 'flusso'

    def _definizione(self):
        from cms.blocks import PageBodyBlock
        return PageBodyBlock()

    def estrai(self, valore):
        from traduzione.flusso import estrai_dal_flusso
        return estrai_dal_flusso(valore, self._definizione())

    def reinserisci(self, valore, testi):
        from traduzione.flusso import reinserisci_nel_flusso
        return reinserisci_nel_flusso(valore, testi, self._definizione())


TESTO = _Testo()
DIZIONARIO = _Dizionario()
DOCUMENTO = _Documento()
RICCO = _Ricco()
FLUSSO = _Flusso()

TUTTI = {g.nome: g for g in (TESTO, DIZIONARIO, DOCUMENTO, RICCO, FLUSSO)}
