"""Modelli pagina.

Due soli tipi, deliberatamente:

- `HomePage`  — la radice del sito, una sola istanza.
- `StandardPage` — tutto il resto. Le pagine non si distinguono per *tipo* ma
  per **quali blocchi contengono**: è ciò che permette a un admin di creare una
  pagina nuova senza che un programmatore aggiunga una classe.

Le pagine Wagtail sono già traducibili quando WAGTAIL_I18N_ENABLED è attivo:
`locale` e `translation_key` arrivano dal modello Page di base.
"""

from django.db import models
from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page
from wagtail_headless_preview.models import HeadlessPreviewMixin

from cms.blocks import PageBodyBlock
from django.contrib.contenttypes.fields import GenericRelation
from traduzione import lingue


class BasePage(HeadlessPreviewMixin, Page):
    """Base comune: anteprima headless verso il frontend Next.js."""

    # Le traduzioni di questa riga. La GenericRelation non serve solo a
    # leggerle comodamente: e' cio' che le fa sparire quando l'oggetto sparisce,
    # visto che `object_id` e' testuale e il database non puo' tenere una
    # chiave esterna vera.
    traduzioni = GenericRelation('traduzione.Traduzione',
                                 content_type_field='content_type',
                                 object_id_field='object_id')

    # In che lingua e' scritta questa pagina.
    #
    # Prima si dava per scontato l'italiano, perche' "le pagine si compongono
    # sempre nella lingua del sito". Non e' vero appena il sito smette di essere
    # di una regione sola: una pagina scritta in inglese veniva mandata al
    # traduttore come se fosse italiana, e la traduzione verso l'inglese chiedeva
    # di tradurre dall'italiano un testo che era gia' inglese.
    source_locale = models.CharField(
        max_length=10, default='it', db_index=True, choices=lingue.scelte,
        verbose_name='lingua di stesura',
        help_text='La lingua in cui stai scrivendo. Il sito la traduce in tutte '
                  'le altre, e a chi legge dice in quale e\' stata scritta.')

    body = StreamField(PageBodyBlock(), blank=True, verbose_name='contenuto')

    content_panels = Page.content_panels + [
        FieldPanel('source_locale'),
        FieldPanel('body'),
    ]

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
