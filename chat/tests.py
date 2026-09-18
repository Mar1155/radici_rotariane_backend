"""Chat: modello, websocket e API REST.

Una chat diretta non e' piu' una riga con due colonne `user1`/`user2`: e' una
chat con esattamente due partecipanti, collegati da `ChatParticipant`. Si
costruisce da `Chat.get_or_create_direct_chat`, che e' anche cio' che
garantisce che fra due persone ce ne sia una sola.
"""

import json

from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Chat, ChatParticipant, Message, MessageTranslation

User = get_user_model()


def crea_utente(nome):
    """L'email e' la chiave di accesso ed e' unica: non si puo' omettere."""
    return User.objects.create_user(
        username=nome, email=f'{nome}@test.com', password='testpass123')


def token(utente):
    return str(RefreshToken.for_user(utente).access_token)


async def connetti(chat, gettone):
    """Apre il websocket e consuma la cronologia.

    Appena accettata la connessione il consumer manda un frame `history` con i
    messaggi gia' scritti. Chi legge subito dopo si trova quello, non il
    proprio messaggio: va tolto di mezzo qui, una volta, invece che in ogni
    test che poi leggerebbe tutto sfasato di uno.
    """
    from backend.asgi import application

    communicator = WebsocketCommunicator(
        application, f"/ws/chat/{chat.id}/?token={gettone}")
    connesso, _ = await communicator.connect()
    assert connesso, 'connessione al websocket rifiutata'
    cronologia = await communicator.receive_json_from(timeout=5)
    assert cronologia['type'] == 'history', cronologia['type']
    return communicator


class ChatModelTest(TestCase):
    """Test per il modello Chat"""

    def setUp(self):
        self.user1 = crea_utente('user1')
        self.user2 = crea_utente('user2')
        self.user3 = crea_utente('user3')

    def test_create_chat(self):
        """Test creazione di una chat tra due utenti"""
        chat = Chat.get_or_create_direct_chat(self.user1, self.user2)
        self.assertIsNotNone(chat.id)
        self.assertEqual(chat.chat_type, 'direct')
        self.assertCountEqual(chat.participants.all(), [self.user1, self.user2])
        self.assertIsNotNone(chat.created_at)

    def test_get_or_create_chat(self):
        """Test del metodo get_or_create_direct_chat"""
        # Crea una nuova chat
        chat1 = Chat.get_or_create_direct_chat(self.user1, self.user2)
        self.assertIsNotNone(chat1.id)

        # Verifica che la stessa chat venga restituita
        chat2 = Chat.get_or_create_direct_chat(self.user1, self.user2)
        self.assertEqual(chat1.id, chat2.id)

        # Verifica che l'ordine degli utenti non importi
        chat3 = Chat.get_or_create_direct_chat(self.user2, self.user1)
        self.assertEqual(chat1.id, chat3.id)

    def test_una_chat_diretta_per_coppia(self):
        """Fra due persone c'e' una sola chat diretta, con chiunque altro un'altra."""
        chat_a = Chat.get_or_create_direct_chat(self.user1, self.user2)
        chat_b = Chat.get_or_create_direct_chat(self.user1, self.user3)

        self.assertNotEqual(chat_a.id, chat_b.id)
        self.assertEqual(Chat.objects.count(), 2)

    def test_chat_unique_constraint(self):
        """Lo stesso utente non puo' entrare due volte nella stessa chat"""
        chat = Chat.get_or_create_direct_chat(self.user1, self.user2)

        with self.assertRaises(Exception):
            ChatParticipant.objects.create(chat=chat, user=self.user1, role='member')


class MessageModelTest(TestCase):
    """Test per il modello Message"""

    def setUp(self):
        self.user1 = crea_utente('user1')
        self.user2 = crea_utente('user2')
        self.chat = Chat.get_or_create_direct_chat(self.user1, self.user2)

    def test_create_message(self):
        """Test creazione di un messaggio"""
        message = Message.objects.create(
            chat=self.chat, sender=self.user1, body="Ciao!"
        )
        self.assertIsNotNone(message.id)
        self.assertEqual(message.chat, self.chat)
        self.assertEqual(message.sender, self.user1)
        self.assertEqual(message.body, "Ciao!")
        self.assertIsNotNone(message.created_at)
        self.assertIsNotNone(message.client_msg_id)

    def test_message_relationship(self):
        """Test della relazione tra Message e Chat"""
        Message.objects.create(chat=self.chat, sender=self.user1, body="Messaggio 1")
        Message.objects.create(chat=self.chat, sender=self.user2, body="Messaggio 2")
        Message.objects.create(chat=self.chat, sender=self.user1, body="Messaggio 3")

        messages = self.chat.messages.all()
        self.assertEqual(messages.count(), 3)


class ChatConsumerTest(TransactionTestCase):
    """Test per il ChatConsumer (WebSocket)"""

    def setUp(self):
        from django.conf import settings

        # Configura in-memory channel layer per i test
        settings.CHANNEL_LAYERS = {
            "default": {
                "BACKEND": "channels.layers.InMemoryChannelLayer"
            }
        }

        self.user1 = crea_utente('user1')
        self.user2 = crea_utente('user2')
        self.user3 = crea_utente('user3')
        self.chat = Chat.get_or_create_direct_chat(self.user1, self.user2)

        self.token_user1 = token(self.user1)
        self.token_user2 = token(self.user2)
        self.token_user3 = token(self.user3)

    async def test_connect_authenticated_participant(self):
        """Test connessione di un utente autenticato e partecipante alla chat"""
        from backend.asgi import application

        communicator = WebsocketCommunicator(
            application,
            f"/ws/chat/{self.chat.id}/?token={self.token_user1}"
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.disconnect()

    async def test_connect_unauthenticated(self):
        """Test connessione di un utente non autenticato"""
        from backend.asgi import application

        communicator = WebsocketCommunicator(
            application,
            f"/ws/chat/{self.chat.id}/"
        )
        connected, code = await communicator.connect()
        self.assertFalse(connected)
        # 4003 = nessun token. Il consumer distingue 4001 scaduto, 4002 non
        # valido, 4003 assente, e il frontend reagisce diversamente a ciascuno.
        self.assertEqual(code, 4003)

    async def test_connect_non_participant(self):
        """Test connessione di un utente che non è partecipante della chat"""
        from backend.asgi import application

        communicator = WebsocketCommunicator(
            application,
            f"/ws/chat/{self.chat.id}/?token={self.token_user3}"
        )
        connected, code = await communicator.connect()
        self.assertFalse(connected)
        self.assertEqual(code, 4403)

    async def test_send_and_receive_message(self):
        """Test invio e ricezione di un messaggio"""
        communicator1 = await connetti(self.chat, self.token_user1)
        communicator2 = await connetti(self.chat, self.token_user2)

        # User1 invia un messaggio
        await communicator1.send_json_to({
            "type": "message.send",
            "body": "Ciao da user1!"
        })

        # User1 riceve il proprio messaggio
        response1 = await communicator1.receive_json_from(timeout=5)
        self.assertEqual(response1["type"], "message")
        self.assertEqual(response1["data"]["body"], "Ciao da user1!")
        self.assertEqual(response1["data"]["sender_id"], self.user1.id)

        # User2 riceve il messaggio di user1
        response2 = await communicator2.receive_json_from(timeout=5)
        self.assertEqual(response2["type"], "message")
        self.assertEqual(response2["data"]["body"], "Ciao da user1!")
        self.assertEqual(response2["data"]["sender_id"], self.user1.id)

        # Verifica che il messaggio sia stato salvato nel database
        @database_sync_to_async
        def check_message():
            message = Message.objects.filter(chat=self.chat, body="Ciao da user1!").first()
            return message is not None

        self.assertTrue(await check_message())

        await communicator1.disconnect()
        await communicator2.disconnect()

    async def test_message_persistence(self):
        """Test che i messaggi vengano salvati correttamente nel database"""
        communicator = await connetti(self.chat, self.token_user1)

        # Invia più messaggi
        messages_to_send = ["Messaggio 1", "Messaggio 2", "Messaggio 3"]
        for msg in messages_to_send:
            await communicator.send_json_to({
                "type": "message.send",
                "body": msg
            })
            # Ricevi la conferma
            await communicator.receive_json_from(timeout=5)

        # Verifica che tutti i messaggi siano nel database
        @database_sync_to_async
        def count_messages():
            return Message.objects.filter(chat=self.chat).count()

        count = await count_messages()
        self.assertEqual(count, len(messages_to_send))

        await communicator.disconnect()


class ChatViewSetTest(APITestCase):
    """Test per le API REST della chat"""

    def setUp(self):
        self.client = APIClient()
        self.user1 = crea_utente('user1')
        self.user2 = crea_utente('user2')
        self.user3 = crea_utente('user3')

        # Crea alcune chat
        self.chat1 = Chat.get_or_create_direct_chat(self.user1, self.user2)
        self.chat2 = Chat.get_or_create_direct_chat(self.user1, self.user3)

        self.token_user1 = token(self.user1)

    def test_list_user_chats(self):
        """Test recupero della lista di chat dell'utente"""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_user1}")
        response = self.client.get("/api/chats/", follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_list_chats_unauthenticated(self):
        """Test che un utente non autenticato non possa accedere alle chat"""
        response = self.client.get("/api/chats/", follow=True)
        self.assertEqual(response.status_code, 401)

    def test_create_direct_chat(self):
        """Test creazione di una chat diretta tra due utenti"""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_user1}")

        # Crea una chat con user2 (dovrebbe restituire la chat esistente)
        response = self.client.post("/api/chats/direct/", {"user_id": self.user2.id}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(self.chat1.id))

    def test_create_direct_chat_new(self):
        """Test creazione di una nuova chat diretta"""
        # Prima elimina la chat esistente
        self.chat1.delete()

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_user1}")
        response = self.client.post("/api/chats/direct/", {"user_id": self.user2.id}, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.data["id"])


class MessageViewSetTest(APITestCase):
    """Test per le API REST dei messaggi"""

    def setUp(self):
        self.client = APIClient()
        self.user1 = crea_utente('user1')
        self.user2 = crea_utente('user2')
        self.chat = Chat.get_or_create_direct_chat(self.user1, self.user2)

        # Crea alcuni messaggi
        for i in range(5):
            Message.objects.create(
                chat=self.chat,
                sender=self.user1 if i % 2 == 0 else self.user2,
                body=f"Messaggio {i}"
            )

        self.token_user1 = token(self.user1)

    def test_list_messages(self):
        """Test recupero della lista di messaggi di una chat"""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_user1}")
        response = self.client.get(f"/api/chats/{self.chat.id}/messages/", follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 5)

    def test_create_message(self):
        """Test creazione di un messaggio via API REST"""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_user1}")
        response = self.client.post(
            f"/api/chats/{self.chat.id}/messages/",
            {"body": "Nuovo messaggio via API"},
            follow=True
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["body"], "Nuovo messaggio via API")
        self.assertEqual(response.data["sender"], self.user1.id)

    def test_messages_unauthenticated(self):
        """Test che un utente non autenticato non possa accedere ai messaggi"""
        response = self.client.get(f"/api/chats/{self.chat.id}/messages/", follow=True)
        self.assertEqual(response.status_code, 401)
