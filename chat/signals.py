from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Chat, ChatParticipant

User = get_user_model()

@receiver(post_save, sender=User)
def sync_user_gemellaggi(sender, instance, created, **kwargs):
    """
    When a user is assigned to a club, add them to all existing Gemellaggio chats of that club.
    """
    if instance.user_type == User.Types.NORMAL and instance.club:
        # Find all gemellaggi involving this club
        gemellaggi = Chat.objects.filter(
            chat_type='gemellaggio',
            related_clubs=instance.club
        )
        
        for chat in gemellaggi:
            ChatParticipant.objects.get_or_create(
                chat=chat,
                user=instance,
                defaults={'role': 'member'}
            )

@receiver(m2m_changed, sender=Chat.related_clubs.through)
def sync_club_gemellaggi(sender, instance, action, reverse, model, pk_set, **kwargs):
    """
    When clubs are added to a Gemellaggio, add all their members to the chat.
    """
    if action == "post_add":
        chat = instance
        if chat.chat_type == 'gemellaggio':
            # Get the added clubs
            clubs = model.objects.filter(pk__in=pk_set)
            
            # Add the clubs themselves as admins
            for club in clubs:
                ChatParticipant.objects.update_or_create(
                    chat=chat,
                    user=club,
                    defaults={'role': 'admin'}
                )
            
            # Get all members of these clubs
            members = User.objects.filter(club__in=clubs)
            
            for member in members:
                ChatParticipant.objects.get_or_create(
                    chat=chat,
                    user=member,
                    defaults={'role': 'member'}
                )
