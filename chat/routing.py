from django.urls import re_path
from .consumers import ChatConsumer, NotificationConsumer, GlobalChatConsumer

websocket_urlpatterns = [
    # Nuovo endpoint globale (stile WhatsApp)
    re_path(r"ws/global/$", GlobalChatConsumer.as_asgi()),
    # Legacy endpoints (mantenuti per compatibilità)
    re_path(r"ws/chat/(?P<chat_id>[0-9a-f-]+)/$", ChatConsumer.as_asgi()),
    re_path(r"ws/notifications/$", NotificationConsumer.as_asgi()),
]