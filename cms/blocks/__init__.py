"""Catalogo dei blocchi componibili.

I nomi dei tipi di blocco sono un **contratto permanente**: StreamField li salva
dentro il JSON di ogni pagina, quindi rinominarne uno rende illeggibili tutte le
pagine che lo usano. Si aggiunge e si deprecano, mai si rinomina.

Ogni blocco corrisponde a un componente React gia' esistente nella webapp: il
CMS non introduce grafica nuova, decide solo quali pezzi mettere e in che
ordine. Colori e superfici sono **token**, non valori liberi: e' cosi' che il
design system resta intatto anche se a comporre le pagine e' chi non scrive
codice.
"""

from .common import (ACCENT_CHOICES, SURFACE_CHOICES, ImmagineBlock,
                     LinkBlock, TipoArticoloBlock, percorso_pagina,
                     url_assoluto)
from .content import PageBodyBlock

__all__ = ['PageBodyBlock', 'LinkBlock', 'ImmagineBlock', 'TipoArticoloBlock',
           'ACCENT_CHOICES', 'SURFACE_CHOICES', 'percorso_pagina', 'url_assoluto']
