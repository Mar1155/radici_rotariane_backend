from django.contrib.auth.models import AbstractUser
from django.db import models

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

    def __str__(self):
        return self.username

    @property
    def has_skills_profile(self):
        """Check if user has completed their skills profile."""
        return self.skills.exists() and self.soft_skills.exists()
