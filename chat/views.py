from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Chat, Message
from .serializers import ChatSerializer, MessageSerializer
from django.shortcuts import get_object_or_404

class ChatViewSet(viewsets.ModelViewSet):
    serializer_class = ChatSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Chat.objects.filter(user1=user) | Chat.objects.filter(user2=user)

    @action(detail=False, methods=["post"])
    def direct(self, request):
        """Crea o recupera la chat diretta con un altro utente."""
        target_id = request.data.get("user_id")
        chat = Chat.get_or_create_chat(request.user, get_object_or_404(request.user.__class__, pk=target_id))
        return Response(ChatSerializer(chat).data)


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        chat_id = self.kwargs.get("chat_pk")
        return Message.objects.filter(chat_id=chat_id).order_by("-id")[:50]

    def perform_create(self, serializer):
        chat = Chat.objects.get(pk=self.kwargs.get("chat_pk"))
        serializer.save(sender=self.request.user, chat=chat)