from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.utils import timezone


class VoceDiCatalogo(models.Model):
    """Base delle tre tabelle che elencano gli attributi di un profilo.

    Sono cataloghi, non testo libero: una competenza e' una **riga**, e il
    nome e' solo la sua etichetta. Questa distinzione e' l'unica cosa che
    rende possibile il multilingua qui, e per un motivo pratico: finche'
    l'identita' di una competenza era il suo nome, mostrarne il nome tradotto
    rompeva il salvataggio — il profilo rimandava indietro "Project
    Management" e il server non trovava "Gestione Progetti".

    Il nome si scrive in italiano, come tutto il resto del sito, e le altre
    lingue stanno dove stanno tutte le traduzioni. Prima c'era un
    `translations = JSONField` qui dentro che conteneva una lingua sola
    (l'italiano, con il nome inglese nella colonna `name`): funzionava in due
    lingue e in nessuna delle altre quattro.
    """

    # Non serve solo a leggere comodamente le traduzioni: e' cio' che le fa
    # sparire insieme alla riga, visto che `object_id` e' testuale e il
    # database non puo' tenere una chiave esterna vera.
    traduzioni = GenericRelation('traduzione.Traduzione',
                                 content_type_field='content_type',
                                 object_id_field='object_id')

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class Skill(VoceDiCatalogo):
    name = models.CharField(max_length=100, unique=True, verbose_name='nome')


class SoftSkill(VoceDiCatalogo):
    name = models.CharField(max_length=100, unique=True, verbose_name='nome')


class FocusArea(VoceDiCatalogo):
    name = models.CharField(max_length=600, unique=True, verbose_name='nome')
    # La sigla ufficiale Rotary dell'area: "A" per una macro area, "A3" per una
    # delle sue voci. Era dentro il JSON delle traduzioni, insieme a due valori
    # che si ricavano da lei, e chi non lo sapeva la ripescava con
    # un'espressione regolare dal nome — in due file diversi, con due
    # risultati che potevano non coincidere.
    code = models.CharField(max_length=8, blank=True, db_index=True,
                            verbose_name='sigla')

    class Meta:
        ordering = ['code', 'name']

    @property
    def macro_code(self) -> str:
        """La lettera della macro area a cui appartiene: "A3" -> "A"."""
        return self.code[:1]

    @property
    def is_macro(self) -> bool:
        """Una macro area e' quella la cui sigla e' la sola lettera."""
        return len(self.code) == 1

class User(AbstractUser):
    class Types(models.TextChoices):
        NORMAL = 'NORMAL', 'Normal User'
        CLUB = 'CLUB', 'Club'

    user_type = models.CharField(max_length=10, choices=Types.choices, default=Types.NORMAL)
    email = models.EmailField(unique=True)
    rotary_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    
    # Profile fields
    profession = models.CharField(max_length=100, blank=True)
    sector = models.CharField(max_length=100, blank=True)
    skills = models.ManyToManyField(Skill, blank=True)
    soft_skills = models.ManyToManyField(SoftSkill, blank=True)
    focus_areas = models.ManyToManyField(FocusArea, blank=True)
    languages = models.JSONField(default=list, blank=True)
    offers_mentoring = models.BooleanField(default=False)
    bio = models.TextField(blank=True)
    club_name = models.CharField(max_length=200, blank=True)
    club = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        limit_choices_to={'user_type': 'CLUB'}, 
        related_name='members'
    )
    location = models.CharField(max_length=200, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)

    # Club specific fields
    club_president = models.CharField(max_length=150, blank=True)
    club_city = models.CharField(max_length=100, blank=True)
    club_country = models.CharField(max_length=100, blank=True)
    club_district = models.CharField(max_length=100, blank=True)
    
    club_latitude = models.FloatField(null=True, blank=True)
    club_longitude = models.FloatField(null=True, blank=True)
    
    club_members_count = models.IntegerField(default=0, help_text="Number of members in the club")
    club_sister_clubs_count = models.IntegerField(default=0, help_text="Number of sister clubs")

    email_verified_at = models.DateTimeField(null=True, blank=True)

    # Use email as the primary login identifier
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']
    EMAIL_FIELD = 'email'

    def __str__(self):
        return self.username

    def save(self, *args, **kwargs):
        # Store empty Rotary ID values as NULL to avoid unique conflicts on ''.
        if self.rotary_id is not None:
            cleaned_rotary_id = self.rotary_id.strip()
            self.rotary_id = cleaned_rotary_id or None
        super().save(*args, **kwargs)

    @property
    def has_skills_profile(self):
        """Check if user has completed their skills profile."""
        return self.skills.exists() and self.soft_skills.exists()

    @property
    def is_email_verified(self):
        return self.email_verified_at is not None


class EmailVerificationToken(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='email_verification_tokens'
    )
    code_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    requested_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['expires_at']),
        ]

    def verify_code(self, code: str) -> bool:
        return check_password(code, self.code_hash)

    @property
    def is_expired(self) -> bool:
        return self.expires_at <= timezone.now()


class PasswordResetToken(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='password_reset_tokens'
    )
    code_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    requested_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['expires_at']),
        ]

    def verify_code(self, code: str) -> bool:
        return check_password(code, self.code_hash)

    @property
    def is_expired(self) -> bool:
        return self.expires_at <= timezone.now()
