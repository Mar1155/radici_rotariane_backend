from django.urls import path
from .views import ChatViewSet, MessageViewSet

chat_list = ChatViewSet.as_view({
    "get": "list",
    "post": "create",
})
chat_detail = ChatViewSet.as_view({
    "get": "retrieve",
    "delete": "destroy",
    "patch": "partial_update",
})
chat_direct = ChatViewSet.as_view({
    "post": "direct",
})

message_list = MessageViewSet.as_view({
    "get": "list",
    "post": "create",
})
message_detail = MessageViewSet.as_view({
    "get": "retrieve",
    "delete": "destroy",
    "patch": "partial_update",
})

urlpatterns = [
    # Chats (il prefisso api/chats/ è già in backend/urls.py)
    path("", chat_list, name="chat-list"),
    # crea o recupera chat diretta
    path("direct/", chat_direct, name="chat-direct"),
    # dettaglio chat
    path("<uuid:pk>/", chat_detail, name="chat-detail"),

    # Messages dentro una chat
    path("<uuid:chat_pk>/messages/", message_list, name="message-list"),
    # dettaglio messaggio
    path("<uuid:chat_pk>/messages/<int:pk>/", message_detail, name="message-detail"),
]