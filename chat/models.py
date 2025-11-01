from django.conf import settings
from django.db import models
from django.utils import timezone
import uuid

class Chat(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user1 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chats_as_user1")
    user2 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chats_as_user2")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user1", "user2"], name="unique_direct_chat"
            )
        ]

    @staticmethod
    def get_or_create_chat(user_a, user_b):
        """Restituisce la chat esistente tra due utenti o la crea."""
        if user_a.id > user_b.id:  # ordina per evitare duplicati inversi
            user_a, user_b = user_b, user_a
        chat, _ = Chat.objects.get_or_create(user1=user_a, user2=user_b)
        return chat


class Message(models.Model):
    id = models.BigAutoField(primary_key=True)
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    body = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    client_msg_id = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)

    class Meta:
        indexes = [models.Index(fields=["chat", "id"])]