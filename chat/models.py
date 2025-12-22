from django.conf import settings
from django.db import models
from django.utils import timezone
import uuid

class Chat(models.Model):
    """
    Modello unificato per chat. Tutte le chat sono tecnicamente "gruppi",
    ma possono avere 2 partecipanti (chat one-to-one) o più partecipanti.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Tipo di chat
    CHAT_TYPE_CHOICES = [
        ('direct', 'Chat Diretta'),
        ('group', 'Chat di Gruppo'),
        ('general_group', 'Chat di Gruppo Generale'),
    ]
    chat_type = models.CharField(max_length=15, choices=CHAT_TYPE_CHOICES, default='direct')
    
    name = models.CharField(max_length=255, blank=True, null=True)  # Nome del gruppo (opzionale per chat dirette)
    description = models.TextField(blank=True, null=True)
    
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        through='ChatParticipant',
        related_name="chats"
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_chats"
    )
    
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(fields=['chat_type', 'created_at']),
        ]

    def __str__(self):
        if self.chat_type in ['group', 'general_group'] and self.name:
            return f"Group: {self.name}"
        elif self.chat_type == 'direct':
            participant_names = " & ".join([p.username for p in self.participants.all()[:2]])
            return f"Direct: {participant_names}" if participant_names else f"Chat {self.id}"
        return f"Chat {self.id}"

    @property
    def is_group(self):
        """Proprietà per mantenere compatibilità con codice esistente."""
        return self.chat_type in ['group', 'general_group']

    @staticmethod
    def get_or_create_direct_chat(user_a, user_b):
        """
        Restituisce la chat diretta esistente tra due utenti o la crea.
        Una chat diretta è semplicemente una chat con esattamente 2 partecipanti.
        """
        from django.db.models import Count
        
        # Cerca una chat diretta esistente tra questi due utenti
        existing_chat = Chat.objects.annotate(
            participant_count=Count('participants')
        ).filter(
            chat_type='direct',
            participant_count=2,
            participants=user_a
        ).filter(
            participants=user_b
        ).first()
        
        if existing_chat:
            return existing_chat
        
        # Crea una nuova chat diretta
        chat = Chat.objects.create(
            chat_type='direct',
            created_by=user_a
        )
        
        # Aggiungi entrambi i partecipanti (nessuno è admin nelle chat dirette)
        ChatParticipant.objects.create(chat=chat, user=user_a, role='member')
        ChatParticipant.objects.create(chat=chat, user=user_b, role='member')
        
        return chat

    @staticmethod
    def create_group(name, creator, participant_ids=None, description=None):
        """Crea una nuova chat di gruppo con più di 2 partecipanti."""
        chat = Chat.objects.create(
            chat_type='group',
            name=name,
            description=description,
            created_by=creator
        )
        
        # Aggiungi il creatore come admin
        ChatParticipant.objects.create(
            chat=chat,
            user=creator,
            role='admin'
        )
        
        # Aggiungi altri partecipanti come membri
        if participant_ids:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            for user_id in participant_ids:
                if user_id != creator.id:
                    try:
                        user = User.objects.get(pk=user_id)
                        ChatParticipant.objects.create(
                            chat=chat,
                            user=user,
                            role='member'
                        )
                    except User.DoesNotExist:
                        pass
        
        return chat


class ChatParticipant(models.Model):
    """Tabella intermedia per tracciare i partecipanti delle chat di gruppo."""
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('member', 'Member'),
    ]
    
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='chat_participants')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ['chat', 'user']
        indexes = [models.Index(fields=['chat', 'user'])]

    def __str__(self):
        return f"{self.user} in {self.chat} ({self.role})"


class Message(models.Model):
    id = models.BigAutoField(primary_key=True)
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    body = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    client_msg_id = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)

    class Meta:
        indexes = [models.Index(fields=["chat", "id"])]


class MessageTranslation(models.Model):
    """Stores cached translations for chat messages."""

    PROVIDER_CHOICES = [
        ('deepl', 'DeepL'),
        ('google', 'Google Cloud Translation'),
    ]

    id = models.BigAutoField(primary_key=True)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='translations')
    target_language = models.CharField(max_length=10)
    translated_text = models.TextField()
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    detected_source_language = models.CharField(max_length=10, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('message', 'target_language')
        indexes = [
            models.Index(fields=['message', 'target_language']),
            models.Index(fields=['target_language']),
        ]

    def __str__(self):
        return f"Translation({self.message_id}, {self.target_language})"