"""Mattoni condivisi fra i blocchi."""

from django.conf import settings
from django.core.exceptions import ValidationError

from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock
from wagtail.snippets.blocks import SnippetChooserBlock

from cms import vocabularies as vocab
from cms.media import url_assoluto

# Superfici ammesse per lo sfondo di una sezione. Sono token, non colori:
# il frontend li traduce in classi Tailwind gia' definite nel design system,
# cosi' non esistono pagine con un blu leggermente diverso dagli altri.
SURFACE_CHOICES = [
    ('white', 'Bianco'),
    ('light', 'Grigio chiaro'),
    ('brand-primary', 'Blu istituzionale'),
    ('brand-secondary', 'Giallo istituzionale'),
    ('brand-gradient', 'Sfumatura istituzionale'),
    ('section', 'Colore della sezione'),
]

# Accenti per icone e bordi.
ACCENT_CHOICES = [
    ('brand-primary', 'Blu istituzionale'),
    ('brand-secondary', 'Giallo'),
    ('emerald', 'Verde'),
    ('amber', 'Ambra'),
    ('rose', 'Rosa'),
    ('sky', 'Azzurro'),
    ('teal', 'Turchese'),
    ('stone', 'Marrone'),
    ('slate', 'Grigio'),
]


class LinkBlock(blocks.StructBlock):
    """Un collegamento: a una pagina del sito, a una rotta o all'esterno.

    `required=False` su uno StructBlock **non** rende opzionali i suoi figli:
    con l'etichetta obbligatoria, un collegamento facoltativo lasciato vuoto
    bloccava comunque il salvataggio della pagina. Qui nessun campo e'
    obbligatorio di per se': e' `clean()` a chiedere l'etichetta soltanto quando
    una destinazione c'e' davvero.
    """

    label = blocks.CharBlock(required=False, label='etichetta')
    page = blocks.PageChooserBlock(required=False, label='pagina del sito')
    route = blocks.CharBlock(required=False, label='percorso interno',
                             help_text='Es. /rota-space')
    external_url = blocks.URLBlock(required=False, label='indirizzo esterno')
    visibility = blocks.ChoiceBlock(choices=vocab.VISIBILITY_CHOICES, default='always',
                                    label='a chi si mostra',
                                    help_text='Un "Iscriviti" non ha senso per chi '
                                              'ha gia\' un account.')

    def clean(self, value):
        risultato = super().clean(value)
        destinazione = (risultato.get('route') or risultato.get('external_url')
                        or risultato.get('page'))
        if destinazione and not risultato.get('label'):
            raise blocks.StructBlockValidationError(
                block_errors={'label': ValidationError(
                    "Indica l'etichetta del pulsante: senza, il collegamento "
                    'sarebbe invisibile.')})
        return risultato

    def get_api_representation(self, value, context=None):
        if not value:
            return None
        # Un collegamento senza destinazione non e' un collegamento: e' un campo
        # facoltativo lasciato vuoto.
        if not (value.get('route') or value.get('external_url') or value.get('page')):
            return None
        pagina = value.get('page')
        href = (value.get('external_url') or value.get('route')
                or (percorso_pagina(pagina) if pagina else None))
        return {
            'label': value.get('label'),
            'href': href,
            'newTab': bool(value.get('external_url')),
            'visibility': value.get('visibility') or 'always',
        }

    class Meta:
        icon = 'link'
        label = 'collegamento'


def percorso_pagina(page) -> str:
    """Percorso di una pagina nel frontend.

    Il sito e' headless: Wagtail non serve HTML, quindi si usa la posizione
    nell'albero togliendo il prefisso della radice.
    """
    if not page:
        return '/'
    percorso = page.url_path or '/'
    sito = page.get_site()
    if sito and sito.root_page:
        prefisso = sito.root_page.url_path
        if percorso.startswith(prefisso):
            percorso = '/' + percorso[len(prefisso):]
    return percorso.rstrip('/') or '/'



class ImmagineBlock(ImageChooserBlock):
    """Immagine con gia' dentro quello che serve a disegnarla."""

    def get_api_representation(self, value, context=None):
        if not value:
            return None
        try:
            resa = value.get_rendition('width-1600')
            url, larghezza, altezza = resa.url, resa.width, resa.height
        except Exception:
            # Se la rendition non si genera (storage lento o file mancante) si
            # ripiega sull'originale invece di far fallire l'intera pagina.
            url, larghezza, altezza = value.file.url, value.width, value.height
        return {
            'url': url_assoluto(url), 'width': larghezza, 'height': altezza,
            'alt': value.title,
            'credit': getattr(value, 'credit', '') or None,
        }


class TipoArticoloBlock(SnippetChooserBlock):
    """Riferimento a un tipo di articolo: al frontend basta la chiave."""

    def __init__(self, **kwargs):
        super().__init__('cms.ArticleType', **kwargs)

    def get_api_representation(self, value, context=None):
        return value.key if value else None
