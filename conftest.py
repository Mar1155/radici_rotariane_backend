"""
Configurazione pytest per i test dell'applicazione chat.
Questo file contiene fixtures condivise e configurazioni per i test.
"""
import pytest
from django.conf import settings
from channels.testing import WebsocketCommunicator
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from chat.models import Chat, Message

User = get_user_model()


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """Setup del database per i test."""
    # Configura il channel layer in-memory per i test
    settings.CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer"
        }
    }


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Abilita l'accesso al database per tutti i test."""
    pass


@pytest.fixture
def test_channel_layers_setting(settings):
    """Configura un channel layer in-memory per i test."""
    settings.CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer"
        }
    }


@pytest.fixture
def create_user():
    """Factory fixture per creare utenti."""
    def _create_user(username, email=None, password="testpass123"):
        if email is None:
            email = f"{username}@test.com"
        return User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
    return _create_user


@pytest.fixture
def user1(create_user):
    """Crea un utente di test."""
    return create_user("user1")


@pytest.fixture
def user2(create_user):
    """Crea un secondo utente di test."""
    return create_user("user2")


@pytest.fixture
def user3(create_user):
    """Crea un terzo utente di test."""
    return create_user("user3")


@pytest.fixture
def chat_between_users(user1, user2):
    """Crea una chat tra due utenti."""
    return Chat.objects.create(user1=user1, user2=user2)


@pytest.fixture
def get_jwt_token():
    """Factory fixture per generare token JWT."""
    def _get_token(user):
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)
    return _get_token


@pytest.fixture
def auth_headers(get_jwt_token):
    """Factory fixture per generare header di autenticazione."""
    def _headers(user):
        token = get_jwt_token(user)
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}
    return _headers
