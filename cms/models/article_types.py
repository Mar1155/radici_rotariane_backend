"""Il tipo di articolo.

Oggi la differenza fra "un progetto da adottare" e "un itinerario" vive dentro
una configurazione duplicata in due repo e modificabile solo da un programmatore
con due deploy coordinati. Questo modello la porta nel database, dove un admin
puo' leggerla e cambiarla.

Lo studio dei 12 tab esistenti mostra che variano **otto dimensioni**, tutte
dati e nessuna codice: campi attivi, quali obbligatori, elementi informativi,
bottoni, colonne, tag ammessi, chi pubblica, link esterni.

Mostra anche che il tipo esiste gia' ma viene **copiato a mano**: `offri` e
`cerca` di scambi-e-mobilita sono identici in tutto, e `storie` e `tradizioni`
hanno gli stessi campi. Restano comunque tipi distinti: se due tab
condividessero un tipo non si distinguerebbero piu' i loro articoli, perche' e'
il tipo a dire a quale elenco appartiene un articolo.
"""

from django.core.exceptions import ValidationError
from django.db import models
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.models import Orderable, TranslatableMixin
from wagtail.search import index

from cms import vocabularies as vocab
from cms.forms import ArticleTypeForm
from django.contrib.contenttypes.fields import GenericRelation


class ArticleType(TranslatableMixin, ClusterableModel, index.Indexed):

    # Le traduzioni di questa riga. La GenericRelation non serve solo a
    # leggerle comodamente: e' cio' che le fa sparire quando l'oggetto sparisce,
    # visto che `object_id` e' testuale e il database non puo' tenere una
    # chiave esterna vera.
    traduzioni = GenericRelation('traduzione.Traduzione',
                                 content_type_field='content_type',
                                 object_id_field='object_id')
    key = models.SlugField(
        max_length=64, verbose_name='chiave',
        help_text="Identificatore tecnico, usato nelle API e negli URL. "
                  "Non cambiarlo dopo che esistono articoli di questo tipo.",
    )
    name = models.CharField(max_length=120, verbose_name='nome singolare',
                            help_text='Es. "Progetto", "Itinerario"')
    name_plural = models.CharField(max_length=120, verbose_name='nome plurale',
                                   help_text='Es. "Progetti", "Itinerari"')
    description = models.TextField(
        blank=True, verbose_name='descrizione',
        help_text='A cosa serve questo tipo. Lo legge chi compone una pagina.',
    )

    # --- Struttura -----------------------------------------------------------
    # active_fields dice quali campi ESISTONO, required_fields quali sono anche
    # OBBLIGATORI. Sono annidati, non paralleli: un campo obbligatorio e'
    # necessariamente attivo. La vecchia coppia required/hidden lasciava
    # possibile un terzo stato ("ne' l'uno ne' l'altro") che il form non sapeva
    # disegnare, e il campo spariva senza errori.
    active_fields = models.JSONField(default=list, blank=True, verbose_name='campi attivi')
    required_fields = models.JSONField(default=list, blank=True, verbose_name='campi obbligatori')

    buttons = models.JSONField(default=list, blank=True, verbose_name='azioni sulla card')
    can_publish = models.JSONField(default=list, blank=True, verbose_name='chi puo pubblicare')
    body_blocks = models.JSONField(default=list, blank=True, verbose_name='blocchi ammessi nel corpo')

    default_columns = models.PositiveSmallIntegerField(
        default=3, choices=vocab.COLUMN_CHOICES, verbose_name='colonne',
        help_text='Quante colonne usa la griglia, se la pagina non dice altro.',
    )
    new_article_label = models.CharField(
        max_length=80, blank=True, verbose_name='etichetta del bottone di creazione',
        help_text='Es. "Proponi progetto". Se vuoto si usa "Nuovo " + nome.',
    )
    uses_geo = models.BooleanField(
        default=False, verbose_name='usa la geografia',
        help_text='Abilita regione e provincia su questo tipo di articolo.',
    )

    # --- Contatti esterni ----------------------------------------------------
    # Alcuni tipi non ospitano articoli propri ma rimandano a un referente
    # esterno (es. i consigli di Casa Calabria International).
    external_url = models.URLField(blank=True, verbose_name='sito esterno')
    external_email = models.EmailField(blank=True, verbose_name='email esterna')
    external_phone = models.CharField(max_length=32, blank=True, verbose_name='telefono esterno')

    base_form_class = ArticleTypeForm

    search_fields = [
        index.SearchField('name'),
        index.SearchField('name_plural'),
        index.AutocompleteField('name'),
    ]

    panels = [
        MultiFieldPanel([
            FieldPanel('name'), FieldPanel('name_plural'),
            FieldPanel('key'), FieldPanel('description'),
        ], heading='Identita'),
        MultiFieldPanel([
            FieldPanel('active_fields'), FieldPanel('required_fields'),
        ], heading='Campi dell articolo'),
        InlinePanel('info_elements', label='Elemento informativo'),
        InlinePanel('allowed_tags', label='Tag'),
        MultiFieldPanel([
            FieldPanel('buttons'), FieldPanel('default_columns'),
        ], heading='Aspetto della card'),
        MultiFieldPanel([
            FieldPanel('can_publish'), FieldPanel('new_article_label'),
            FieldPanel('body_blocks'), FieldPanel('uses_geo'),
        ], heading='Pubblicazione'),
        MultiFieldPanel([
            FieldPanel('external_url'), FieldPanel('external_email'),
            FieldPanel('external_phone'),
        ], heading='Contatti esterni', classname='collapsed'),
    ]

    class Meta(TranslatableMixin.Meta):
        verbose_name = 'tipo di articolo'
        verbose_name_plural = 'tipi di articolo'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['key', 'locale'], name='uniq_articletype_key_locale'),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        errors = {}
        sconosciuti = set(self.active_fields or []) - set(vocab.FIELD_KEYS)
        if sconosciuti:
            errors['active_fields'] = f"Campi non riconosciuti: {sorted(sconosciuti)}"
        # Il vincolo che rende impossibile ricreare il vecchio bug.
        orfani = set(self.required_fields or []) - set(self.active_fields or [])
        if orfani:
            errors['required_fields'] = (
                f"Questi campi sono obbligatori ma non attivi: {sorted(orfani)}. "
                "Un campo obbligatorio deve essere anche attivo, altrimenti "
                "l'autore non potrebbe compilarlo."
            )
        # Un campo obbligatorio che non si puo' soddisfare blocca del tutto la
        # pubblicazione, e dal form non si capisce perche': si chiede un tag e
        # non ce n'e' nessuno da scegliere.
        if self.pk:
            if 'tags' in (self.required_fields or []) and not self.allowed_tags.exists():
                errors['required_fields'] = (
                    "I tag sono obbligatori ma questo tipo non ne ammette nessuno: "
                    "nessuno potrebbe pubblicare. Aggiungi dei tag, oppure togli "
                    "'tags' dai campi obbligatori."
                )
            if ('infoElements' in (self.required_fields or [])
                    and not self.info_elements.exists()):
                errors['required_fields'] = (
                    "Gli elementi informativi sono obbligatori ma questo tipo non "
                    "ne definisce nessuno."
                )
        if errors:
            raise ValidationError(errors)

    # --- Comodita' per il resto del codice ----------------------------------
    def field_is_active(self, field: str) -> bool:
        return field in (self.active_fields or [])

    def field_is_required(self, field: str) -> bool:
        return field in (self.required_fields or [])

    @property
    def create_label(self) -> str:
        return self.new_article_label or f'Nuovo {self.name.lower()}'


class ArticleTypeInfoElement(TranslatableMixin, Orderable):
    """Un dato sintetico mostrato sulla card (Importo, Durata, Scadenza...).

    `key` e' l'identita' stabile del dato: e' con quella che il valore viene
    salvato sull'articolo. Nella configurazione attuale gli stessi valori sono
    un array posizionale, quindi riordinare gli elementi corrompe in silenzio
    tutti gli articoli gia' scritti.
    """

    # Le traduzioni di questa riga. La GenericRelation non serve solo a
    # leggerle comodamente: e' cio' che le fa sparire quando l'oggetto sparisce,
    # visto che `object_id` e' testuale e il database non puo' tenere una
    # chiave esterna vera.
    traduzioni = GenericRelation('traduzione.Traduzione',
                                 content_type_field='content_type',
                                 object_id_field='object_id')

    article_type = ParentalKey(ArticleType, on_delete=models.CASCADE,
                               related_name='info_elements')
    key = models.SlugField(max_length=40, verbose_name='chiave')
    icon = models.CharField(max_length=40, choices=vocab.ICON_CHOICES, verbose_name='icona')
    label = models.CharField(max_length=80, verbose_name='etichetta')

    panels = [FieldPanel('key'), FieldPanel('icon'), FieldPanel('label')]

    class Meta(TranslatableMixin.Meta, Orderable.Meta):
        verbose_name = 'elemento informativo'
        verbose_name_plural = 'elementi informativi'

    def __str__(self):
        return f'{self.label} ({self.key})'


class ArticleTypeTag(TranslatableMixin, Orderable):
    """Un tag tematico ammesso su questo tipo.

    La geografia NON passa di qui: ha una tassonomia gerarchica propria, perche'
    una lista piatta non regge 20 regioni e oltre 100 province.
    """

    # Le traduzioni di questa riga. La GenericRelation non serve solo a
    # leggerle comodamente: e' cio' che le fa sparire quando l'oggetto sparisce,
    # visto che `object_id` e' testuale e il database non puo' tenere una
    # chiave esterna vera.
    traduzioni = GenericRelation('traduzione.Traduzione',
                                 content_type_field='content_type',
                                 object_id_field='object_id')

    article_type = ParentalKey(ArticleType, on_delete=models.CASCADE,
                               related_name='allowed_tags')
    key = models.SlugField(max_length=60, verbose_name='chiave')
    label = models.CharField(max_length=80, verbose_name='etichetta')

    panels = [FieldPanel('key'), FieldPanel('label')]

    class Meta(TranslatableMixin.Meta, Orderable.Meta):
        verbose_name = 'tag'
        verbose_name_plural = 'tag'

    def __str__(self):
        return self.label
