import uuid
from django.db import models
from django.conf import settings


class Post(models.Model):
    """A forum post with title and description."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField()
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='forum_posts'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Comment(models.Model):
    """A comment on a forum post."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        related_name='replies',
        null=True,
        blank=True
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='forum_comments'
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author.username} on {self.post.title}"


class PostTranslation(models.Model):
    """Stores cached translations for forum posts."""

    PROVIDER_CHOICES = [
        ('deepl', 'DeepL'),
        ('google', 'Google Cloud Translation'),
    ]

    id = models.BigAutoField(primary_key=True)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='translations')
    target_language = models.CharField(max_length=10)
    translated_title = models.CharField(max_length=255)
    translated_description = models.TextField()
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    detected_source_language = models.CharField(max_length=10, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('post', 'target_language')
        indexes = [
            models.Index(fields=['post', 'target_language']),
            models.Index(fields=['target_language']),
        ]

    def __str__(self):
        return f"Translation({self.post_id}, {self.target_language})"
