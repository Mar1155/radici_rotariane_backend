import uuid
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation


class Post(models.Model):
    """A forum post with title and description."""

    # Le traduzioni di questa riga. La GenericRelation non serve solo a
    # leggerle comodamente: e' cio' che le fa sparire quando l'oggetto sparisce,
    # visto che `object_id` e' testuale e il database non puo' tenere una
    # chiave esterna vera.
    traduzioni = GenericRelation('traduzione.Traduzione',
                                 content_type_field='content_type',
                                 object_id_field='object_id')
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

    # Le traduzioni di questa riga. La GenericRelation non serve solo a
    # leggerle comodamente: e' cio' che le fa sparire quando l'oggetto sparisce,
    # visto che `object_id` e' testuale e il database non puo' tenere una
    # chiave esterna vera.
    traduzioni = GenericRelation('traduzione.Traduzione',
                                 content_type_field='content_type',
                                 object_id_field='object_id')
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
