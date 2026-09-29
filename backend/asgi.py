import os, django
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

# Import after django.setup() to avoid ImproperlyConfigured error
from .middleware.jwt_ws import JwtAuthMiddleware  # se usi JWT per WS
from chat.routing import websocket_urlpatterns
from traduzione import coda

# Da qui, e solo da qui: e' l'unico punto che viene eseguito dal server e non
# da `manage.py`. Accende il lavoratore che traduce in sottofondo cio' che
# viene pubblicato, e gli fa recuperare cio' che era rimasto indietro mentre
# il processo era giu'.
coda.avvia()

application = ProtocolTypeRouter({
    "http": get_asgi_application(),  # gestisce le API REST
    "websocket": JwtAuthMiddleware(  # gestisce le WS
        URLRouter(websocket_urlpatterns)
    ),
})