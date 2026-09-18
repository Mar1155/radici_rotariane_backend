"""Utility del forum.

La sanitizzazione del testo ricco e' passata in `common/richtext.py`: la usano
anche le biografie di soci e club, e `users` non deve dipendere da `forum`.
"""

from common.richtext import (  # noqa: F401  (ri-esportati per compatibilita')
    ATTRIBUTI_AMMESSI as ALLOWED_RICH_TEXT_ATTRIBUTES,
    TAG_AMMESSI as ALLOWED_RICH_TEXT_TAGS,
    sanitize_rich_text,
)
