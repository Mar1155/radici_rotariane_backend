from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.db import models
from django.utils import timezone

class Skill(models.Model):
    name = models.CharField(max_length=100, unique=True)
    translations = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.name

class SoftSkill(models.Model):
    name = models.CharField(max_length=100, unique=True)
    translations = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.name


class FocusArea(models.Model):
    name = models.CharField(max_length=100, unique=True)
    translations = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.name

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
