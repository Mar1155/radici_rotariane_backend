"""Catalogo dei blocchi componibili.

I nomi dei tipi di blocco sono un **contratto permanente**: StreamField li
salva dentro il JSON di ogni pagina, quindi rinominarne uno rende illeggibili
tutte le pagine che lo usano. Si aggiunge e si deprecano, non si rinomina.

In questa fase c'è solo `rich_text`, che è il minimo per rendere una pagina
utilizzabile. Il catalogo completo — hero, griglie, liste articoli, CTA —
arriva con la fase di composizione pagine, un blocco per ogni componente React
già esistente nella webapp.
"""

from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock

RICH_TEXT_FEATURES = [
    'h2', 'h3', 'h4', 'bold', 'italic', 'link', 'document-link',
    'ol', 'ul', 'hr', 'blockquote',
]


class PageBodyBlock(blocks.StreamBlock):
    rich_text = blocks.RichTextBlock(
        features=RICH_TEXT_FEATURES, label='testo'
    )
    image = ImageChooserBlock(label='immagine')

    class Meta:
        block_counts = {}
        label = 'contenuto'
