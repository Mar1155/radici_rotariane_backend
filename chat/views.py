from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from .models import Chat, ChatParticipant, Message, MessageTranslation
from .serializers import (
    ChatSerializer,
    CreateGroupChatSerializer,
    MessageSerializer,
    MessageTranslationSerializer,
)
from .services.translation import (
    TranslationProviderError,
    TranslationServiceNotConfigured,
    normalize_language_code,
    supported_languages,
    translate_text,
)

class ChatViewSet(viewsets.ModelViewSet):
    serializer_class = ChatSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Restituisce tutte le chat in cui l'utente è partecipante."""
        user = self.request.user
        return Chat.objects.filter(participants=user).distinct()

    @action(detail=False, methods=["post"])
    def direct(self, request):
        """Crea o recupera la chat diretta con un altro utente."""
        target_id = request.data.get("user_id")
        target_user = get_object_or_404(request.user.__class__, pk=target_id)
        chat = Chat.get_or_create_direct_chat(request.user, target_user)
        return Response(ChatSerializer(chat).data)

    @action(detail=False, methods=["post"])
    def create_group(self, request):
        """Crea una nuova chat di gruppo."""
        serializer = CreateGroupChatSerializer(data=request.data)
        if serializer.is_valid():
            chat = Chat.create_group(
                name=serializer.validated_data['name'],
                creator=request.user,
                participant_ids=serializer.validated_data.get('participant_ids', [])
            )
            # Imposta la descrizione se fornita
            if serializer.validated_data.get('description'):
                chat.description = serializer.validated_data['description']
                chat.save()
            
            return Response(
                ChatSerializer(chat).data,
                status=status.HTTP_201_CREATED
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def add_participant(self, request, pk=None):
        """Aggiunge un partecipante a una chat di gruppo."""
        chat = self.get_object()
        
        if chat.chat_type == 'direct':
            return Response(
                {"error": "Non puoi aggiungere partecipanti alle chat dirette. Crea un gruppo invece."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verifica che l'utente sia admin
        participant = ChatParticipant.objects.filter(chat=chat, user=request.user).first()
        if not participant or participant.role != 'admin':
            return Response(
                {"error": "Solo gli admin possono aggiungere partecipanti."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        user_id = request.data.get("user_id")
        if not user_id:
            return Response(
                {"error": "user_id è richiesto."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user_to_add = get_object_or_404(request.user.__class__, pk=user_id)
        
        # Verifica se l'utente è già nel gruppo
        if ChatParticipant.objects.filter(chat=chat, user=user_to_add).exists():
            return Response(
                {"error": "L'utente è già nel gruppo."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ChatParticipant.objects.create(chat=chat, user=user_to_add, role='member')
        return Response(ChatSerializer(chat).data)

    @action(detail=True, methods=["post"])
    def remove_participant(self, request, pk=None):
        """Rimuove un partecipante da una chat di gruppo."""
        chat = self.get_object()
        
        if chat.chat_type == 'direct':
            return Response(
                {"error": "Non puoi rimuovere partecipanti dalle chat dirette."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verifica che l'utente sia admin
        requester = ChatParticipant.objects.filter(chat=chat, user=request.user).first()
        if not requester or requester.role != 'admin':
            return Response(
                {"error": "Solo gli admin possono rimuovere partecipanti."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        user_id = request.data.get("user_id")
        if not user_id:
            return Response(
                {"error": "user_id è richiesto."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        participant_to_remove = ChatParticipant.objects.filter(
            chat=chat, 
            user_id=user_id
        ).first()
        
        if not participant_to_remove:
            return Response(
                {"error": "L'utente non è nel gruppo."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        participant_to_remove.delete()
        return Response(ChatSerializer(chat).data)

    @action(detail=True, methods=["post"])
    def leave_group(self, request, pk=None):
        """Permette a un utente di uscire da una chat di gruppo."""
        chat = self.get_object()
        
        if chat.chat_type == 'direct':
            return Response(
                {"error": "Non puoi uscire da una chat diretta. Puoi solo eliminarla."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        participant = ChatParticipant.objects.filter(chat=chat, user=request.user).first()
        if not participant:
            return Response(
                {"error": "Non fai parte di questo gruppo."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        participant.delete()
        
        # Se era l'ultimo partecipante, elimina la chat
        if chat.chat_participants.count() == 0:
            chat.delete()
            return Response({"message": "Gruppo eliminato (ultimo partecipante uscito)."})
        
        return Response({"message": "Sei uscito dal gruppo."})


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_chat(self):
        chat_id = self.kwargs.get("chat_pk")
        chat = get_object_or_404(Chat, pk=chat_id)
        if not chat.participants.filter(pk=self.request.user.pk).exists():
            raise PermissionDenied("Non fai parte di questa chat.")
        return chat

    def get_queryset(self):
        chat = self.get_chat()
        return Message.objects.filter(chat=chat).select_related("sender").order_by("-created_at")

    def perform_create(self, serializer):
        chat = self.get_chat()
        serializer.save(sender=self.request.user, chat=chat)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())[:50]
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def translate(self, request, *args, **kwargs):
        message = self.get_object()
        target_language = request.data.get("target_language") or request.query_params.get(
            "target_language"
        )

        if not target_language:
            return Response(
                {"detail": "target_language è obbligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        normalized_language = normalize_language_code(target_language)
        if normalized_language not in supported_languages():
            return Response(
                {"detail": "Lingua di destinazione non supportata."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing = MessageTranslation.objects.filter(
            message=message, target_language=normalized_language
        ).first()
        if existing:
            serializer = MessageTranslationSerializer(existing)
            return Response(serializer.data)

        shared_translation = (
            MessageTranslation.objects.filter(
                target_language=normalized_language,
                message__body=message.body,
            )
            .exclude(message=message)
            .order_by("created_at")
            .first()
        )
        if shared_translation:
            with transaction.atomic():
                translation = MessageTranslation.objects.create(
                    message=message,
                    target_language=normalized_language,
                    translated_text=shared_translation.translated_text,
                    provider=shared_translation.provider,
                    detected_source_language=shared_translation.detected_source_language,
                )
            serializer = MessageTranslationSerializer(translation)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if not message.body.strip():
            return Response(
                {"detail": "Il messaggio è vuoto, impossibile tradurre."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = translate_text(message.body, normalized_language)
        except TranslationServiceNotConfigured:
            return Response(
                {"detail": "Nessun provider di traduzione configurato."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except TranslationProviderError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        with transaction.atomic():
            translation, _created = MessageTranslation.objects.get_or_create(
                message=message,
                target_language=normalized_language,
                defaults={
                    "translated_text": result.text,
                    "provider": result.provider,
                    "detected_source_language": result.detected_source_language,
                },
            )

        serializer = MessageTranslationSerializer(translation)
        http_status = status.HTTP_201_CREATED if _created else status.HTTP_200_OK
        return Response(serializer.data, status=http_status)