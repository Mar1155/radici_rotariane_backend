from rest_framework import serializers
from .models import Chat, Message, ChatParticipant
from django.contrib.auth import get_user_model

User = get_user_model()

class MessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    
    class Meta:
        model = Message
        fields = ["id", "chat", "sender", "sender_username", "body", "created_at", "client_msg_id"]


class ChatParticipantSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = ChatParticipant
        fields = ['user_id', 'username', 'role', 'joined_at']


class ChatSerializer(serializers.ModelSerializer):
    participants_details = ChatParticipantSerializer(source='chat_participants', many=True, read_only=True)
    participant_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Chat
        fields = [
            "id", "chat_type", "name", "description",
            "created_by", "created_at", "participants_details", "participant_count"
        ]
        read_only_fields = ["id", "created_at", "created_by"]

    def get_participant_count(self, obj):
        return obj.chat_participants.count()


class CreateGroupChatSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    participant_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True
    )

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Il nome del gruppo non può essere vuoto.")
        return value

    def validate_participant_ids(self, value):
        if value:
            # Verifica che gli utenti esistano
            existing_users = User.objects.filter(id__in=value).count()
            if existing_users != len(value):
                raise serializers.ValidationError("Alcuni ID utente non sono validi.")
        return value