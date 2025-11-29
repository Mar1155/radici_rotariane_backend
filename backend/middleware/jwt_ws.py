from urllib.parse import parse_qs
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import close_old_connections
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.conf import settings
from channels.db import database_sync_to_async
import jwt


class JwtAuthMiddleware:
    """
    Middleware per Django Channels che autentica via JWT.
    Supporta sia token nel querystring (?token=...) sia nell'header Authorization.
    """

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        return await JwtAuthMiddlewareInstance(scope, self)(receive, send)


class JwtAuthMiddlewareInstance:
    def __init__(self, scope, middleware):
        self.scope = dict(scope)
        self.middleware = middleware

    async def __call__(self, receive, send):
        self.scope["user"], self.scope["token_error"] = await self.get_user()
        close_old_connections()
        inner = self.middleware.inner
        return await inner(self.scope, receive, send)

    async def get_user(self):
        query_string = parse_qs(self.scope.get("query_string", b"").decode())
        headers = dict(self.scope.get("headers", []))
        token = None

        # 1️⃣ Token da query string: ws://...?token=<JWT>
        if "token" in query_string:
            token = query_string["token"][0]

        # 2️⃣ Token da header Authorization: Bearer <JWT>
        elif b"authorization" in headers:
            auth_header = headers[b"authorization"].decode()
            if auth_header.lower().startswith("bearer "):
                token = auth_header.split(" ")[1]

        if not token:
            return AnonymousUser(), "no_token"

        try:
            # Valida il token con SimpleJWT
            UntypedToken(token)
            decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user_id = decoded.get("user_id")
            if user_id is None:
                return AnonymousUser(), "invalid_token"

            user = await database_sync_to_async(get_user_model().objects.get)(id=user_id)
            return user, None
        except jwt.ExpiredSignatureError:
            return AnonymousUser(), "token_expired"
        except (InvalidToken, TokenError, jwt.DecodeError):
            return AnonymousUser(), "invalid_token"
        except get_user_model().DoesNotExist:
            return AnonymousUser(), "user_not_found"