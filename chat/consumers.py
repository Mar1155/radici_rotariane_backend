from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Chat, Message, ChatParticipant

class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.chat_id = self.scope["url_route"]["kwargs"]["chat_id"]
        self.group_name = f"chat_{self.chat_id}"
        user = self.scope["user"]
        token_error = self.scope.get("token_error")

        # Controllo autenticazione
        if not user.is_authenticated:
            # Codici di chiusura specifici per il frontend:
            # 4001 = Token scaduto (richiede refresh)
            # 4002 = Token invalido (richiede re-login)
            # 4003 = Nessun token fornito
            if token_error == "token_expired":
                await self.close(code=4001)  # Token expired - frontend può fare refresh
            elif token_error == "invalid_token":
                await self.close(code=4002)  # Invalid token
            elif token_error == "user_not_found":
                await self.close(code=4002)  # User not found
            else:
                await self.close(code=4003)  # No token
            return

        # Controllo che l'utente faccia parte della chat (diretta o gruppo)
        if not await self._is_participant(user.id):
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        
        # Invia la history dei messaggi
        history = await self._get_message_history()
        await self.send_json({"type": "history", "data": history})

    async def disconnect(self, code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content):
        if content.get("type") == "message.send":
            msg = await self._create_message(self.scope["user"].id, content.get("body", ""))
            await self.channel_layer.group_send(
                self.group_name, {"type": "message.created", "message": msg}
            )

    async def message_created(self, event):
        await self.send_json({"type": "message", "data": event["message"]})

    @database_sync_to_async
    def _is_participant(self, user_id):
        """Verifica se l'utente fa parte della chat."""
        try:
            chat = Chat.objects.get(id=self.chat_id)
            return ChatParticipant.objects.filter(
                chat=chat,
                user_id=user_id
            ).exists()
        except Chat.DoesNotExist:
            return False

    @database_sync_to_async
    def _get_message_history(self, limit=50):
        """Recupera gli ultimi messaggi della chat."""
        messages = Message.objects.filter(chat_id=self.chat_id).order_by('-created_at')[:limit]
        # Restituisce i messaggi dal più recente al più vecchio
        return [
            {
                "id": msg.id,
                "sender_id": msg.sender_id,
                "body": msg.body,
                "created_at": msg.created_at.isoformat()
            }
            for msg in messages
        ]

    # Crea un nuovo messaggio nel database quando viene ricevuto, in modo asincrono per non bloccare il consumer
    @database_sync_to_async
    def _create_message(self, user_id, body):
        msg = Message.objects.create(chat_id=self.chat_id, sender_id=user_id, body=body)
        return {"id": msg.id, "sender_id": user_id, "body": msg.body, "created_at": msg.created_at.isoformat()}