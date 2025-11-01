import os, django
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

# Import after django.setup() to avoid ImproperlyConfigured error
from .middleware.jwt_ws import JwtAuthMiddleware  # se usi JWT per WS
from chat.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": get_asgi_application(),  # gestisce le API REST
    "websocket": JwtAuthMiddleware(  # gestisce le WS
        URLRouter(websocket_urlpatterns)
    ),
})