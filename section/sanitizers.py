"""Sanitizzazione dell'HTML degli articoli (Card.content).

Policy separata da quella del forum (`forum/utils.py`): un articolo è un
documento ricco — immagini, titoli, citazioni — mentre un post di forum è una
discussione breve. Tenerle distinte evita di allargare la superficie del forum
per un bisogno che ha solo la sezione articoli.

NOTA TEMPORANEA (rimuovere insieme alla riscrittura dell'editor):
`data:` è ammesso fra i protocolli di `img[src]` finché l'editor in uso resta
Quill, che inlinea in base64 ogni immagine incollata perché non esiste un
endpoint di upload. Vietarlo adesso non proteggerebbe da nulla — un'immagine
`data:` in un tag <img> non esegue script, nemmeno se SVG — e farebbe sparire
in silenzio le immagini a chi sta usando la webapp nel frattempo.

Va rimosso nella fase "editor articoli", insieme al passaggio a TipTap e
all'upload su MediaAsset: è quello, non questa allowlist, a impedire che nuovo
base64 entri nel database. Le card attualmente in DB non sono un vincolo (il
database sarà azzerato), lo è solo l'editor ancora in uso.
"""

from __future__ import annotations

import bleach
from bleach.css_sanitizer import CSSSanitizer

ALLOWED_TAGS = [
    'p', 'br', 'hr', 'span', 'div',
    'strong', 'b', 'em', 'i', 'u', 's', 'sub', 'sup',
    'h1', 'h2', 'h3', 'h4',
    'ul', 'ol', 'li',
    'blockquote', 'pre', 'code',
    'a', 'img', 'figure', 'figcaption',
]

ALLOWED_ATTRIBUTES = {
    '*': ['class'],
    'a': ['href', 'title', 'target', 'rel'],
    'img': ['src', 'alt', 'title', 'width', 'height'],
    'li': ['data-list'],           # Quill marca i bullet così
    'p': ['style'],
    'h1': ['style'], 'h2': ['style'], 'h3': ['style'], 'h4': ['style'],
    'span': ['style'],
    'blockquote': ['style'],
}

ALLOWED_PROTOCOLS = ['http', 'https', 'mailto', 'data']

_css_sanitizer = CSSSanitizer(
    allowed_css_properties=['text-align', 'color', 'background-color']
)

_cleaner = bleach.Cleaner(
    tags=ALLOWED_TAGS,
    attributes=ALLOWED_ATTRIBUTES,
    protocols=ALLOWED_PROTOCOLS,
    css_sanitizer=_css_sanitizer,
    strip=True,
)


def sanitize_article_html(value):
    """Ripulisce l'HTML di un articolo. Accetta None e restituisce None."""
    if not value:
        return value
    return _cleaner.clean(value).strip()
