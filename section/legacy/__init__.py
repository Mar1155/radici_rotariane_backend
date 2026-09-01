"""Snapshot congelato della configurazione sezioni/tab pre-migrazione.

`config_snapshot.json` è la fotografia byte-per-byte della configurazione che
oggi vive duplicata in due repo:

  - frontend  app/scopri/config/{sections.structure,sections.metadata,
              sections.translations,tabs.metadata}.ts
  - backend   section/structure.py  (STRUCTURE_CONFIG)

Serve a una cosa sola: fare da riferimento al **test di equivalenza**. Quando la
configurazione si sposterà nel database, il seed dovrà riprodurre esattamente
questo snapshot, e il test lo verificherà campo per campo. Senza un riferimento
congelato non c'è modo di dimostrare che la migrazione non ha perso nulla.

NON modificare a mano. Va rigenerato solo se la config attuale cambia prima
della migrazione, con:

    cd <frontend> && node scripts/dump-legacy-config.mjs \
        > ../radici_rotariane_backend/section/legacy/config_snapshot.json

Al termine della migrazione (quando `app/scopri/config/` sarà cancellato e il
DB sarà l'unica sorgente) questo pacchetto va rimosso.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_SNAPSHOT = Path(__file__).parent / 'config_snapshot.json'


@lru_cache(maxsize=1)
def legacy_config() -> dict:
    """Restituisce lo snapshot completo (strutture + metadati + traduzioni)."""
    with _SNAPSHOT.open(encoding='utf-8') as fh:
        return json.load(fh)


def legacy_tabs():
    """Itera le coppie (sezione, tab, config-del-tab) dello snapshot."""
    for section, sdata in legacy_config()['structureConfig'].items():
        for tab, tdata in sdata['tabs'].items():
            yield section, tab, tdata
