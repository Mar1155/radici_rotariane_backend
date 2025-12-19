from django.db import models
from django.utils.text import slugify
from django.contrib.postgres.fields import ArrayField
from django.conf import settings


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
        ("partner-e-collaborazioni", "Partner e Collaborazioni"),
        ("eccellenze-calabresi", "Eccellenze Calabresi"),
        ("eventi", "Eventi")
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