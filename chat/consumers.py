from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Chat, Message
from django.db.models import Q

class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.chat_id = self.scope["url_route"]["kwargs"]["chat_id"]
        user = self.scope["user"]

        # Controllo autenticazione
        if not user.is_authenticated:
            await self.close(code=4401)
            return

        # Controllo che l'utente faccia parte della chat
        if not await self._is_participant(user.id):
            await self.close(code=4403)
            return

        self.group_name = f"chat_{self.chat_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        
        # Invia la history dei messaggi
        history = await self._get_message_history()
        await self.send_json({"type": "history", "data": history})

    async def disconnect(self, code):
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
        return Chat.objects.filter(id=self.chat_id).filter(
            Q(user1_id=user_id) | Q(user2_id=user_id)
        ).exists()

    @database_sync_to_async
    def _get_message_history(self, limit=50):
        """Recupera gli ultimi messaggi della chat."""
        messages = Message.objects.filter(chat_id=self.chat_id).order_by('-created_at')[:limit]
        # Inverti l'ordine per avere i messaggi dal più vecchio al più recente
        return [
            {
                "id": msg.id,
                "sender_id": msg.sender_id,
                "body": msg.body,
                "created_at": msg.created_at.isoformat()
            }
            for msg in reversed(messages)
        ]

    # Crea un nuovo messaggio nel database quando viene ricevuto, in modo asincrono per non bloccare il consumer
    @database_sync_to_async
    def _create_message(self, user_id, body):
        msg = Message.objects.create(chat_id=self.chat_id, sender_id=user_id, body=body)
        return {"id": msg.id, "sender_id": user_id, "body": msg.body, "created_at": msg.created_at.isoformat()}