"""Sanitizzazione del testo ricco scritto da una persona.

E' la policy per i campi HTML brevi compilati dagli utenti: la biografia di un
socio o di un club, il testo di un post. Corrisponde a cio' che l'editor
condiviso (`RichTextEditor`) sa produrre: se un giorno l'editor guadagna un
pulsante, questa lista va allargata insieme.

Il corpo degli **articoli** non passa di qui: non e' HTML ma un documento
strutturato, validato per schema in `section/schema.py`. Sono due problemi
diversi e due soluzioni diverse — qui si vieta, li' si copia solo il previsto.
"""

from __future__ import annotations

import bleach
from bleach.css_sanitizer import CSSSanitizer

TAG_AMMESSI = [
    'p', 'strong', 'em', 'u', 's', 'blockquote', 'ul', 'ol', 'li', 'a',
    'h1', 'h2', 'h3', 'br', 'span',
]

ATTRIBUTI_AMMESSI = {
    '*': ['class'],
    'a': ['href', 'title', 'target', 'rel'],
    'p': ['style'],
    'h1': ['style'],
    'h2': ['style'],
    'h3': ['style'],
    'span': ['style'],
}

_css = CSSSanitizer(allowed_css_properties=['text-align'])
_cleaner = bleach.Cleaner(
    tags=TAG_AMMESSI,
    attributes=ATTRIBUTI_AMMESSI,
    css_sanitizer=_css,
    strip=True,
)


def sanitize_rich_text(value: str) -> str:
    """L'HTML ridotto al sottoinsieme che sappiamo trattare."""
    if not value:
        return ''
    return _cleaner.clean(value).strip()
