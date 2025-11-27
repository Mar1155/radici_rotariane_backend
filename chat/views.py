from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Chat, Message, ChatParticipant
from .serializers import ChatSerializer, MessageSerializer, CreateGroupChatSerializer
from django.shortcuts import get_object_or_404

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

    def get_queryset(self):
        chat_id = self.kwargs.get("chat_pk")
        return Message.objects.filter(chat_id=chat_id).order_by("-id")[:50]

    def perform_create(self, serializer):
        chat = Chat.objects.get(pk=self.kwargs.get("chat_pk"))
        serializer.save(sender=self.request.user, chat=chat)