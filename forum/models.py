import uuid
from django.db import models
from django.conf import settings


class Post(models.Model):
    """A forum post with title and description."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField()
    source_locale = models.CharField(max_length=10, default='it', db_index=True,
                                     verbose_name='lingua di stesura')
    content_html = models.TextField(blank=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='forum_posts'
    )
    comments_read_at = models.DateTimeField(null=True, blank=True)
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
    source_locale = models.CharField(max_length=10, default='it', db_index=True,
                                     verbose_name='lingua di stesura')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author.username} on {self.post.title}"


class PostTranslation(models.Model):
    """Un post del forum in un'altra lingua, tenuto in cache."""

    PROVIDER_CHOICES = [
        ('claude', 'Modello linguistico'),
        ('identita', 'Nessuna traduzione (testo originale)'),
        ('umano', 'Scritta da una persona'),
    ]

    id = models.BigAutoField(primary_key=True)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='translations')
    target_language = models.CharField(max_length=10)
    # TextField per lo stesso motivo di CardTranslation: le traduzioni si
    # espandono e update_or_create non valida la lunghezza.
    translated_title = models.TextField()
    translated_description = models.TextField()
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    detected_source_language = models.CharField(max_length=10, blank=True, null=True)
    needs_review = models.BooleanField(default=False, db_index=True)
    human_locked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('post', 'target_language')
        indexes = [
            models.Index(fields=['post', 'target_language']),
            models.Index(fields=['target_language']),
        ]

    def __str__(self):
        return f"Translation({self.post_id}, {self.target_language})"

class CommentTranslation(models.Model):
    """Un commento in un'altra lingua.

    Mancava: una discussione aveva il post traducibile e le risposte no, cioe'
    proprio la parte in cui si conversa fra lingue diverse.
    """

    PROVIDER_CHOICES = PostTranslation.PROVIDER_CHOICES

    id = models.BigAutoField(primary_key=True)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE,
                                related_name='translations')
    target_language = models.CharField(max_length=10)
    translated_text = models.TextField()
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    needs_review = models.BooleanField(default=False, db_index=True)
    human_locked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('comment', 'target_language')
        indexes = [models.Index(fields=['comment', 'target_language'])]

    def __str__(self):
        return f'CommentTranslation({self.comment_id}, {self.target_language})'
