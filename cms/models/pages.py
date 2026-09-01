"""Modelli pagina.

Due soli tipi, deliberatamente:

- `HomePage`  — la radice del sito, una sola istanza.
- `StandardPage` — tutto il resto. Le pagine non si distinguono per *tipo* ma
  per **quali blocchi contengono**: è ciò che permette a un admin di creare una
  pagina nuova senza che un programmatore aggiunga una classe.

Le pagine Wagtail sono già traducibili quando WAGTAIL_I18N_ENABLED è attivo:
`locale` e `translation_key` arrivano dal modello Page di base.
"""

from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page
from wagtail_headless_preview.models import HeadlessPreviewMixin

from cms.blocks import PageBodyBlock


class BasePage(HeadlessPreviewMixin, Page):
    """Base comune: anteprima headless verso il frontend Next.js."""

    body = StreamField(PageBodyBlock(), blank=True, verbose_name='contenuto')

    content_panels = Page.content_panels + [FieldPanel('body')]

    class Meta:
        abstract = True


class HomePage(BasePage):
    max_count = 1

    class Meta:
        verbose_name = 'home page'
        verbose_name_plural = 'home page'


class StandardPage(BasePage):
    class Meta:
        verbose_name = 'pagina'
        verbose_name_plural = 'pagine'
