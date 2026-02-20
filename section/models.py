from django.db import models
from django.utils.text import slugify
from django.contrib.postgres.fields import ArrayField
from django.conf import settings
from django.core.exceptions import ValidationError


class Card(models.Model):
    
    DATE_TYPE_CHOICES = [
        ('single', 'Data Singola'),
        ('range', 'Range di Date'),
        ('none', 'Nessuna Data'),
    ]

    SECTION_CHOICES = [
        ("storie-e-radici", "Storie e Radici"),
        ("scopri-la-calabria", "Scopri la Calabria"),
        ("scambi-e-mobilita", "Scambi e Mobilità"),
        ("adotta-un-progetto", "Adotta un Progetto"),
        ("eccellenze-calabresi", "Eccellenze Calabresi"),
        ("calendario-delle-radici", "Calendario delle Radici"),
        ("archivio", "Archivio")
    ]
    
    # Campi base
    section = models.CharField(
        max_length=30,
        choices=SECTION_CHOICES,
        null=True,
        blank=True,
        verbose_name="Sezione",
    )

    tab = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Tab",
        help_text="Tab specifica all'interno della sezione"
    )

    title = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Titolo",
        help_text="Titolo della card"
    )

    subtitle = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="Sottotitolo",
        help_text="Sottotitolo/descrizione breve"
    )

    location = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Localizzazione",
        help_text="Luogo o locazione della card"
    )

    slug = models.SlugField(
        max_length=255,
        unique=True,
        blank=True,
        help_text="URL-friendly version del titolo (generato automaticamente)"
    )

    # Immagine di copertina
    cover_image = models.ImageField(
        upload_to='cards/covers/%Y/%m/',
        null=True,
        blank=True,
        verbose_name="Immagine di copertina",
        help_text="Immagine principale della card"
    )
    
    # Tags - usa ArrayField se PostgreSQL, altrimenti JSONField
    # Per PostgreSQL:
    '''
    tags = ArrayField(
        models.CharField(max_length=50),
        blank=True,
        default=list,
        verbose_name="Tags",
        help_text="Lista di tag associati alla card"
    )
    '''
    
    # Se usi MySQL/SQLite invece di PostgreSQL:
    from django.db.models import JSONField
    tags = JSONField(
        default=list,
        blank=True,
        verbose_name="Tags"
    )
    
    # Contenuto ricco (HTML dall'editor)
    # TextField supporta testo molto grande (fino a ~2GB in PostgreSQL)
    content = models.TextField(
        null=True,
        blank=True,
        verbose_name="Contenuto",
        help_text="Contenuto HTML dell'articolo"
    )
    
    # Gestione date
    date_type = models.CharField(
        max_length=10,
        choices=DATE_TYPE_CHOICES,
        default='single',
        verbose_name="Tipo di data"
    )
    
    date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data evento",
        help_text="Data singola dell'evento"
    )
    
    date_start = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data inizio",
        help_text="Data inizio per eventi con range"
    )
    
    date_end = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data fine",
        help_text="Data fine per eventi con range"
    )
    
    # Metadati
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data creazione"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Ultimo aggiornamento"
    )
    
    is_published = models.BooleanField(
        default=True,
        verbose_name="Pubblicato",
        help_text="La card è visibile pubblicamente"
    )
    
    # Campi opzionali utili
    views_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Visualizzazioni"
    )
    
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cards',
        verbose_name="Autore"
    )
    
    # Array di valori per gli elementi info
    from django.db.models import JSONField
    infoElementValues = JSONField(
        default=list,
        null=True,
        blank=True,
        verbose_name="Info Element Values",
        help_text="Array di valori per gli elementi info (uno per ogni tupla della sezione/tab)"
    )
    
    class Meta:
        verbose_name = "Card"
        verbose_name_plural = "Cards"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['slug']),
            models.Index(fields=['is_published', '-created_at']),
        ]
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        """
        Override save to generate slug and call full_clean() for validation.
        """
        # Genera automaticamente lo slug dal titolo se non esiste
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            
            # Gestisci slug duplicati aggiungendo un numero
            while Card.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            self.slug = slug

        self.full_clean()
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('card-detail', kwargs={'slug': self.slug})
    
    @property
    def get_display_date(self):
        """
        Restituisce la data formattata in base al tipo
        """
        if self.date_type == 'single' and self.date:
            return self.date.strftime('%d %B %Y')
        elif self.date_type == 'range' and self.date_start and self.date_end:
            return f"{self.date_start.strftime('%d %B')} - {self.date_end.strftime('%d %B %Y')}"
        return "Data non specificata"
    
    @property
    def is_past_event(self):
        """
        Controlla se l'evento è passato
        """
        from datetime import date
        today = date.today()
        
        if self.date_type == 'single' and self.date:
            return self.date < today
        elif self.date_type == 'range' and self.date_end:
            return self.date_end < today
        
        return False

    def validate_consistency(self) -> None:
        """
        Validate card consistency with the structure configuration.
        
        Ensures:
        - Section and tab are valid
        - All tags belong to the allowed set for this section-tab
        - Info elements count matches expected count
        
        Raises:
            ValidationError: If any consistency check fails
        """
        from section.structure import validate_card_consistency

        tags = self.tags if isinstance(self.tags, list) else []
        info_elements_count = len(self.infoElementValues) if self.infoElementValues else 0

        # Solo consistenza dati (section, tab, tags, info elements).
        # I permessi utente sono già verificati nella view.
        is_valid, errors = validate_card_consistency(
            section=self.section,
            tab=self.tab,
            tags=tags,
            info_elements_count=info_elements_count,
        )
        if not is_valid:
            raise ValidationError(errors)

    def clean(self) -> None:
        """
        Called during model validation (e.g., in forms and admin).
        Validates both field-level and model-level constraints.
        """
        super().clean()
        self.validate_consistency()

class CardAttachment(models.Model):
    FILE_TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
        ('file', 'File'),
    ]

    card = models.ForeignKey(
        Card,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    file = models.FileField(upload_to='cards/gallery/%Y/%m/')
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES, default='file')
    original_name = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Card Attachment'
        verbose_name_plural = 'Card Attachments'
        ordering = ['uploaded_at']

    def __str__(self):
        return self.original_name or self.file.name


class CardReport(models.Model):
    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name='reports')
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='card_reports'
    )
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Card Report'
        verbose_name_plural = 'Card Reports'
        ordering = ['-created_at']

    def __str__(self):
        return f"Report #{self.pk} for {self.card_id}"


class CardTranslation(models.Model):
    PROVIDER_CHOICES = [
        ('deepl', 'DeepL'),
        ('google', 'Google Cloud Translation'),
    ]

    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name='translations')
    target_language = models.CharField(max_length=10)
    translated_title = models.CharField(max_length=255)
    translated_subtitle = models.TextField(blank=True)
    translated_content = models.TextField(blank=True)
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    detected_source_language = models.CharField(max_length=10, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('card', 'target_language')
        indexes = [
            models.Index(fields=['card', 'target_language']),
            models.Index(fields=['target_language']),
        ]

    def __str__(self):
        return f"CardTranslation({self.card_id}, {self.target_language})"


class SavedCard(models.Model):
    """Modello per le card salvate/preferite dagli utenti"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='saved_cards',
        verbose_name='Utente'
    )
    card = models.ForeignKey(
        Card,
        on_delete=models.CASCADE,
        related_name='saved_by',
        verbose_name='Card'
    )
    created_at = models.DateTimeField(auto_now_add=True, db_column='saved_at', verbose_name='Data salvataggio')

    class Meta:
        verbose_name = 'Card Salvata'
        verbose_name_plural = 'Card Salvate'
        unique_together = ('user', 'card')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user} → {self.card}"