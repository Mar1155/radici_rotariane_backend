"""Menu di navigazione come dati.

Oggi la navigazione e' scritta a mano **due volte**: un array in Navbar.tsx e
di nuovo, come JSX, in Footer.tsx. Gli stessi undici link compaiono in entrambi,
e aggiungerne uno significa ricordarsi di due posti e fare un deploy.

Qui i menu sono contenuto. Il pezzo che elimina davvero la duplicazione e'
`MenuItem.submenu`: una voce puo' puntare a un altro menu invece che a una
pagina, cosi' "Esplora" e' definito una volta sola e viene usato sia come
tendina nella barra sia come colonna del footer.
"""

from django.core.exceptions import ValidationError
from django.db import models
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.models import Orderable, TranslatableMixin

from cms import vocabularies as vocab


class Menu(TranslatableMixin, ClusterableModel):
    key = models.SlugField(
        max_length=64, verbose_name='chiave',
        help_text='Identificatore usato dal frontend. Non cambiarlo se il menu '
                  'e gia in uso.',
    )
    name = models.CharField(max_length=120, verbose_name='nome')
    description = models.TextField(
        blank=True, verbose_name='descrizione',
        help_text='A cosa serve questo menu e dove compare.',
    )

    panels = [
        FieldPanel('name'), FieldPanel('key'), FieldPanel('description'),
        InlinePanel('items', label='Voce'),
    ]

    class Meta(TranslatableMixin.Meta):
        verbose_name = 'menu'
        verbose_name_plural = 'menu'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['key', 'locale'], name='uniq_menu_key_locale'),
        ]

    def __str__(self):
        return self.name


class MenuItem(TranslatableMixin, Orderable):
    class Visibilita(models.TextChoices):
        """Le stesse tre scelte di `vocab.VISIBILITY_CHOICES`, che valgono anche
        per i pulsanti dentro le pagine."""

        SEMPRE = 'always', 'Sempre'
        AUTENTICATI = 'authenticated', 'Solo a chi ha fatto accesso'
        ANONIMI = 'anonymous', 'Solo a chi non ha fatto accesso'

    menu = ParentalKey(Menu, on_delete=models.CASCADE, related_name='items')
    label = models.CharField(max_length=120, verbose_name='etichetta')

    # --- Destinazione: esattamente una delle quattro -------------------------
    page = models.ForeignKey(
        'wagtailcore.Page', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', verbose_name='pagina del sito',
        help_text='Una pagina creata nel CMS.',
    )
    route = models.CharField(
        max_length=200, blank=True, verbose_name='percorso interno',
        help_text="Una rotta dell'applicazione, es. /rota-space. "
                  'Serve per le pagine che restano codice.',
    )
    external_url = models.URLField(blank=True, verbose_name='indirizzo esterno')
    submenu = models.ForeignKey(
        'cms.Menu', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='usato_da', verbose_name='sottomenu',
        help_text='Invece di una destinazione, apre un altro menu. E cosi che '
                  '"Esplora" viene definito una volta e usato in piu punti.',
    )

    icon = models.CharField(max_length=40, blank=True, choices=vocab.ICON_CHOICES,
                            verbose_name='icona')
    visibility = models.CharField(max_length=16, choices=Visibilita.choices,
                                  default=Visibilita.SEMPRE, verbose_name='visibile')
    roles = models.JSONField(
        default=list, blank=True, verbose_name='solo per questi ruoli',
        help_text='Lascia vuoto per mostrarla a tutti.',
    )
    open_in_new_tab = models.BooleanField(default=False, verbose_name='apri in una nuova scheda')

    panels = [
        FieldPanel('label'),
        MultiFieldPanel([
            FieldPanel('page'), FieldPanel('route'),
            FieldPanel('external_url'), FieldPanel('submenu'),
        ], heading='Destinazione (scegline una)'),
        MultiFieldPanel([
            FieldPanel('icon'), FieldPanel('visibility'),
            FieldPanel('roles'), FieldPanel('open_in_new_tab'),
        ], heading='Aspetto e visibilita', classname='collapsed'),
    ]

    class Meta(TranslatableMixin.Meta, Orderable.Meta):
        verbose_name = 'voce di menu'
        verbose_name_plural = 'voci di menu'

    def __str__(self):
        return self.label

    def clean(self):
        super().clean()
        scelte = [bool(self.page_id), bool(self.route), bool(self.external_url), bool(self.submenu_id)]
        n = sum(scelte)
        if n == 0:
            raise ValidationError({'route': 'Indica una destinazione: pagina, percorso, '
                                            'indirizzo esterno o sottomenu.'})
        if n > 1:
            raise ValidationError({'route': 'Indica una sola destinazione.'})
        if self.submenu_id and self.submenu_id == self.menu_id:
            raise ValidationError({'submenu': 'Un menu non puo contenere se stesso.'})

    @property
    def href(self) -> str | None:
        """Indirizzo risolto, o None se la voce apre un sottomenu."""
        if self.external_url:
            return self.external_url
        if self.route:
            return self.route
        if self.page_id:
            # Il sito e headless: Wagtail non serve HTML, quindi si usa il
            # percorso nell'albero togliendo il prefisso della radice.
            percorso = self.page.url_path or '/'
            radice = self.page.get_site()
            if radice and radice.root_page:
                prefisso = radice.root_page.url_path
                if percorso.startswith(prefisso):
                    percorso = '/' + percorso[len(prefisso):]
            return percorso.rstrip('/') or '/'
        return None
