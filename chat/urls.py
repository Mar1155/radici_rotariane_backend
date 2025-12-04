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
chat_create_group = ChatViewSet.as_view({
    "post": "create_group",
})
chat_add_participant = ChatViewSet.as_view({
    "post": "add_participant",
})
chat_remove_participant = ChatViewSet.as_view({
    "post": "remove_participant",
})
chat_leave_group = ChatViewSet.as_view({
    "post": "leave_group",
})
chat_forum = ChatViewSet.as_view({
    "get": "forum",
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
message_translate = MessageViewSet.as_view({
    "post": "translate",
})

urlpatterns = [
    # Chats (il prefisso api/chats/ è già in backend/urls.py)
    path("", chat_list, name="chat-list"),
    # crea o recupera chat diretta
    path("direct/", chat_direct, name="chat-direct"),
    # recupera forum globale
    path("forum/", chat_forum, name="chat-forum"),
    # crea gruppo
    path("create_group/", chat_create_group, name="chat-create-group"),
    # dettaglio chat
    path("<uuid:pk>/", chat_detail, name="chat-detail"),
    # aggiungi partecipante al gruppo
    path("<uuid:pk>/add_participant/", chat_add_participant, name="chat-add-participant"),
    # rimuovi partecipante dal gruppo
    path("<uuid:pk>/remove_participant/", chat_remove_participant, name="chat-remove-participant"),
    # esci dal gruppo
    path("<uuid:pk>/leave_group/", chat_leave_group, name="chat-leave-group"),

    # Messages dentro una chat
    path("<uuid:chat_pk>/messages/", message_list, name="message-list"),
    # dettaglio messaggio
    path("<uuid:chat_pk>/messages/<int:pk>/", message_detail, name="message-detail"),
    # traduzione messaggio
    path("<uuid:chat_pk>/messages/<int:pk>/translate/", message_translate, name="message-translate"),
]