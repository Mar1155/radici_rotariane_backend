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

    
    # Campi base


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
    # Documento ProseMirror, non HTML. La forma e la validazione stanno in
    # `section/schema.py`, insieme alla ragione per cui non e' HTML.
    body = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Corpo",
        help_text="Documento strutturato dell'articolo"
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
    
    # In che lingua e' stato scritto. Serve a sapere cosa tradurre e cosa no,
    # e a dire al lettore "scritto originariamente in italiano".
    source_locale = models.CharField(
        max_length=10, default='it', db_index=True,
        verbose_name='lingua di stesura')

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

    # --- Nuovo modello: il tipo di articolo ---------------------------------
    # Sostituisce la coppia (section, tab), che resta finche' il frontend non
    # passa al nuovo modello. PROTECT perche' cancellare un tipo che ha
    # articoli e' quasi sempre un errore: prima si spostano gli articoli.
    article_type = models.ForeignKey(
        'cms.ArticleType',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='cards',
        verbose_name='tipo di articolo',
    )

    # Valori degli elementi informativi indicizzati per CHIAVE.
    # `infoElementValues` qui sopra e' un array posizionale allineato all'ordine
    # della configurazione: riordinare gli elementi corrompe in silenzio tutti
    # gli articoli gia' scritti. Con la chiave questo non puo' succedere.
    info_values = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='valori informativi',
        help_text='Mappa chiave -> valore degli elementi informativi.',
    )

    # Area geografica strutturata. Sostituisce `location`, che e' testo libero:
    # con 107 province il testo libero non e' filtrabile ne' aggregabile.
    # `location` resta finche' il form non passa al nuovo campo.
    geo_area = models.ForeignKey(
        'cms.GeoArea',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cards',
        verbose_name='area geografica',
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
        """Verifica che l'articolo sia coerente con il suo tipo.

        Il tipo dice quali tag sono ammessi e quali elementi informativi
        esistono: qui si controlla che l'articolo non ne usi altri.
        """
        tipo = self.article_type
        if tipo is None:
            raise ValidationError({'article_type': 'Indica il tipo di articolo.'})

        errori = {}

        tag = self.tags if isinstance(self.tags, list) else []
        ammessi = set(tipo.allowed_tags.values_list('key', flat=True))
        non_ammessi = [t for t in tag if t not in ammessi]
        if non_ammessi:
            errori['tags'] = (
                f"Tag non previsti dal tipo «{tipo.name}»: {sorted(non_ammessi)}."
            )

        valori = self.info_values if isinstance(self.info_values, dict) else {}
        chiavi = set(tipo.info_elements.values_list('key', flat=True))
        sconosciute = [k for k in valori if k not in chiavi]
        if sconosciute:
            errori['info_values'] = (
                f"Elementi informativi non previsti dal tipo «{tipo.name}»: "
                f"{sorted(sconosciute)}."
            )

        if errori:
            raise ValidationError(errori)

    def clean(self) -> None:
        """
        Called during model validation (e.g., in forms and admin).
        Validates both field-level and model-level constraints.
        """
        super().clean()
        self.validate_consistency()

class MediaAsset(models.Model):
    """Un'immagine caricata, riferita dal corpo di un articolo.

    Il corpo memorizza l'**identificativo**, non un indirizzo: se un giorno i
    file si spostano (altro bucket, altro dominio), gli articoli non vanno
    toccati. Un indirizzo dentro il testo e' una dipendenza nascosta che si
    scopre solo quando si rompe.
    """

    file = models.ImageField(upload_to='articoli/%Y/%m/', verbose_name='file')
    # Sul contenuto normalizzato: caricare due volte la stessa foto non
    # duplica niente.
    checksum = models.CharField(max_length=64, unique=True, db_index=True,
                                verbose_name='impronta')
    width = models.PositiveIntegerField(verbose_name='larghezza')
    height = models.PositiveIntegerField(verbose_name='altezza')
    byte_size = models.PositiveIntegerField(verbose_name='peso in byte')
    alt = models.CharField(max_length=255, blank=True, verbose_name='testo alternativo')
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='media', verbose_name='caricata da')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'immagine'
        verbose_name_plural = 'immagini'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.file.name} ({self.width}x{self.height})'


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
    """La versione di un articolo in un'altra lingua.

    Una riga per lingua: aggiungerne una non richiede migrazioni, che e' cio'
    che rende vero "aggiungere una lingua costa tre righe di configurazione".
    """

    PROVIDER_CHOICES = [
        ('claude', 'Modello linguistico'),
        ('deepl', 'DeepL'),
        ('google', 'Google Cloud Translation'),
        ('identita', 'Nessuna traduzione (testo originale)'),
        ('umano', 'Scritta da una persona'),
    ]

    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name='translations')
    target_language = models.CharField(max_length=10)
    # TextField, non CharField(255): una traduzione IT→DE si espande del 10-30%
    # e update_or_create non chiama full_clean(), quindi l'eccesso arriverebbe
    # a Postgres come errore 'value too long' invece che come ValidationError.
    translated_title = models.TextField()
    translated_subtitle = models.TextField(blank=True)
    translated_location = models.TextField(blank=True)
    # Il corpo tradotto e' un documento, non testo: i nodi di testo si
    # sostituiscono al loro posto e la formattazione non passa dal traduttore.
    translated_body = models.JSONField(null=True, blank=True)
    translated_info_values = models.JSONField(default=dict, blank=True)

    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    detected_source_language = models.CharField(max_length=10, blank=True, null=True)

    # Una correzione fatta a mano non va sovrascritta dalla ri-traduzione
    # automatica: chi l'ha scritta ne sapeva piu' della macchina.
    human_locked = models.BooleanField(
        default=False, verbose_name='corretta a mano')
    # Tradotta senza un motore vero, o con un motore che non garantisce il
    # glossario: e' la coda di revisione.
    needs_review = models.BooleanField(
        default=False, db_index=True, verbose_name='da rivedere')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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