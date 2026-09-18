"""Quali immagini cita un corpo di articolo.

Serve al serializer per risolverle e, piu' avanti, per sapere quali file sono
ancora riferiti da qualcuno.
"""

from __future__ import annotations


def identificativi_media(documento) -> list[int]:
    """Gli id delle immagini citate, nell'ordine in cui compaiono."""
    trovati: list[int] = []

    def visita(nodo):
        if not isinstance(nodo, dict):
            return
        attrs = nodo.get('attrs') or {}
        if nodo.get('type') == 'image' and isinstance(attrs.get('assetId'), int):
            trovati.append(attrs['assetId'])
        elif nodo.get('type') == 'gallery':
            trovati.extend(i for i in (attrs.get('assetIds') or [])
                           if isinstance(i, int))
        for figlio in nodo.get('content') or []:
            visita(figlio)

    visita(documento)
    # Senza ripetizioni, ma conservando l'ordine.
    return list(dict.fromkeys(trovati))
