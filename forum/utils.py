"""Utility helpers for the forum app."""

from __future__ import annotations

import bleach
from bleach.css_sanitizer import CSSSanitizer

ALLOWED_RICH_TEXT_TAGS = [
    'p', 'strong', 'em', 'u', 's', 'blockquote', 'ul', 'ol', 'li', 'a',
    'h1', 'h2', 'h3', 'br', 'span'
]

ALLOWED_RICH_TEXT_ATTRIBUTES = {
    '*': ['class'],
    'a': ['href', 'title', 'target', 'rel'],
    'p': ['style'],
    'h1': ['style'],
    'h2': ['style'],
    'h3': ['style'],
    'span': ['style'],
}

_css_sanitizer = CSSSanitizer(allowed_css_properties=['text-align'])
_rich_text_cleaner = bleach.Cleaner(
    tags=ALLOWED_RICH_TEXT_TAGS,
    attributes=ALLOWED_RICH_TEXT_ATTRIBUTES,
    css_sanitizer=_css_sanitizer,
    strip=True,
)


def sanitize_rich_text(value: str) -> str:
    """Sanitize rich text HTML to the subset that we support."""
    if not value:
        return ''
    return _rich_text_cleaner.clean(value).strip()
