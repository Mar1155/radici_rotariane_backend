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
            if token_error == "token_expired":
                await self.close(code=4001)
            elif token_error == "invalid_token":
                await self.close(code=4002)
            elif token_error == "user_not_found":
                await self.close(code=4002)
            else:
                await self.close(code=4003)
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
            sender_id = self.scope["user"].id
            msg = await self._create_message(sender_id, content.get("body", ""))
            # Invia il messaggio nella chat room
            await self.channel_layer.group_send(
                self.group_name, {"type": "message.created", "message": msg}
            )
            # Notifica tutti i partecipanti (per aggiornare badge non-letti)
            participant_ids = await self._get_other_participant_ids(sender_id)
            for uid in participant_ids:
                unread = await self._get_unread_count_for_user(uid)
                await self.channel_layer.group_send(
                    f"user_{uid}",
                    {
                        "type": "unread.update",
                        "chat_id": str(self.chat_id),
                        "unread_count": unread,
                    },
                )

    async def message_created(self, event):
        await self.send_json({"type": "message", "data": event["message"]})

    # ── helpers ──────────────────────────────────────────────

    @database_sync_to_async
    def _is_participant(self, user_id):
        try:
            chat = Chat.objects.get(id=self.chat_id)
            return ChatParticipant.objects.filter(chat=chat, user_id=user_id).exists()
        except Chat.DoesNotExist:
            return False

    @database_sync_to_async
    def _get_message_history(self, limit=50):
        messages = Message.objects.filter(chat_id=self.chat_id).order_by('-created_at')[:limit]
        return [
            {
                "id": msg.id,
                "sender_id": msg.sender_id,
                "body": msg.body,
                "created_at": msg.created_at.isoformat(),
            }
            for msg in messages
        ]

    @database_sync_to_async
    def _create_message(self, user_id, body):
        msg = Message.objects.create(chat_id=self.chat_id, sender_id=user_id, body=body)
        return {
            "id": msg.id,
            "sender_id": user_id,
            "body": msg.body,
            "created_at": msg.created_at.isoformat(),
        }

    @database_sync_to_async
    def _get_other_participant_ids(self, sender_id):
        return list(
            ChatParticipant.objects.filter(chat_id=self.chat_id)
            .exclude(user_id=sender_id)
            .values_list("user_id", flat=True)
        )

    @database_sync_to_async
    def _get_unread_count_for_user(self, user_id):
        part = (
            ChatParticipant.objects.filter(chat_id=self.chat_id, user_id=user_id)
            .only("last_read_at", "joined_at")
            .first()
        )
        if not part:
            return 0
        last_read = part.last_read_at or part.joined_at
        return (
            Message.objects.filter(chat_id=self.chat_id, created_at__gt=last_read)
            .exclude(sender_id=user_id)
            .count()
        )


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """
    Canale per-utente. Il frontend si connette a ws/notifications/
    e riceve aggiornamenti in tempo reale sui messaggi non letti.
    """

    async def connect(self):
        user = self.scope["user"]
        token_error = self.scope.get("token_error")

        if not user.is_authenticated:
            if token_error == "token_expired":
                await self.close(code=4001)
            elif token_error == "invalid_token":
                await self.close(code=4002)
            else:
                await self.close(code=4003)
            return

        self.user_group = f"user_{user.id}"
        await self.channel_layer.group_add(self.user_group, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, "user_group"):
            await self.channel_layer.group_discard(self.user_group, self.channel_name)

    async def unread_update(self, event):
        """Inoltra l'evento di aggiornamento non-letti al client."""
        await self.send_json(
            {
                "type": "unread_update",
                "chat_id": event["chat_id"],
                "unread_count": event["unread_count"],
            }
        )