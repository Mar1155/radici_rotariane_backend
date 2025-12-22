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
    email = models.EmailField(unique=True)
    
    # Profile fields
    profession = models.CharField(max_length=100, blank=True)
    sector = models.CharField(max_length=100, blank=True)
    skills = models.ManyToManyField(Skill, blank=True)
    soft_skills = models.ManyToManyField(SoftSkill, blank=True)
    languages = models.JSONField(default=list, blank=True)
    offers_mentoring = models.BooleanField(default=False)
    bio = models.TextField(blank=True)
    club_name = models.CharField(max_length=200, blank=True)
    location = models.CharField(max_length=200, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)

    def __str__(self):
        return self.username

    @property
    def has_skills_profile(self):
        """Check if user has completed their skills profile."""
        return self.skills.exists() and self.soft_skills.exists()