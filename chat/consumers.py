from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import Chat, Message, ChatParticipant


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """Legacy per-chat WebSocket consumer (mantenuto per compatibilità)."""

    async def connect(self):
        self.chat_id = self.scope["url_route"]["kwargs"]["chat_id"]
        self.group_name = f"chat_{self.chat_id}"
        user = self.scope["user"]
        token_error = self.scope.get("token_error")

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

        if not await self._is_participant(user.id):
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        history = await self._get_message_history()
        await self.send_json({"type": "history", "data": history})

    async def disconnect(self, code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content):
        if content.get("type") == "message.send":
            sender_id = self.scope["user"].id
            msg = await self._create_message(sender_id, content.get("body", ""))
            await self.channel_layer.group_send(
                self.group_name, {"type": "chat.message", "message": msg, "chat_id": str(self.chat_id)}
            )
            participant_ids = await self._get_other_participant_ids(sender_id)
            for uid in participant_ids:
                unread = await self._get_unread_count_for_user(uid)
                await self.channel_layer.group_send(
                    f"user_{uid}",
                    {
                        "type": "unread.update",
                        "chat_id": str(self.chat_id),
                        "chat_type": await self._get_chat_type(),
                        "unread_count": unread,
                    },
                )

    async def chat_message(self, event):
        """Handles chat.message from channel layer (unified event name)."""
        await self.send_json({"type": "message", "data": event["message"]})

    # Legacy handler for backward compatibility
    async def message_created(self, event):
        await self.send_json({"type": "message", "data": event["message"]})

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
                "client_msg_id": str(msg.client_msg_id),
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
            "client_msg_id": str(msg.client_msg_id),
        }

    @database_sync_to_async
    def _get_other_participant_ids(self, sender_id):
        return list(
            ChatParticipant.objects.filter(chat_id=self.chat_id)
            .exclude(user_id=sender_id)
            .values_list("user_id", flat=True)
        )

    @database_sync_to_async
    def _get_chat_type(self):
        try:
            return Chat.objects.get(id=self.chat_id).chat_type
        except Chat.DoesNotExist:
            return ""

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
    Legacy canale per-utente (mantenuto per compatibilità).
    Il nuovo frontend usa GlobalChatConsumer.
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
                "chat_type": event.get("chat_type", ""),
                "unread_count": event["unread_count"],
            }
        )


class GlobalChatConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket globale per utente (stile WhatsApp).
    Una singola connessione riceve messaggi da TUTTE le chat dell'utente
    e gestisce l'invio messaggi, mark-read, e aggiornamenti unread in tempo reale.
    
    Endpoint: ws/global/
    
    Messaggi in ingresso dal client:
        - { type: "message.send", chat_id: "...", body: "..." }
        - { type: "mark_read", chat_id: "..." }
        - { type: "chat.join", chat_id: "..." }
    
    Messaggi in uscita verso il client:
        - { type: "init", data: { unread_counts: { chat_id: { unread_count, chat_type } } } }
        - { type: "new_message", chat_id: "...", data: { id, sender_id, body, created_at, client_msg_id } }
        - { type: "unread_update", chat_id: "...", chat_type: "...", unread_count: N }
        - { type: "error", message: "..." }
    """

    async def connect(self):
        user = self.scope["user"]
        token_error = self.scope.get("token_error")

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

        self.user = user
        self.user_group = f"user_{user.id}"
        self.chat_groups = set()

        # Entra nel gruppo notifiche personale
        await self.channel_layer.group_add(self.user_group, self.channel_name)

        # Entra in tutti i gruppi chat dell'utente
        chat_ids = await self._get_user_chat_ids()
        for chat_id in chat_ids:
            group_name = f"chat_{chat_id}"
            self.chat_groups.add(group_name)
            await self.channel_layer.group_add(group_name, self.channel_name)

        await self.accept()

        # Invia i conteggi non-letti iniziali
        unread_counts = await self._get_all_unread_counts()
        await self.send_json({
            "type": "init",
            "data": {"unread_counts": unread_counts},
        })

    async def disconnect(self, code):
        if hasattr(self, "user_group"):
            await self.channel_layer.group_discard(self.user_group, self.channel_name)
        if hasattr(self, "chat_groups"):
            for group_name in self.chat_groups:
                await self.channel_layer.group_discard(group_name, self.channel_name)

    async def receive_json(self, content):
        msg_type = content.get("type")

        if msg_type == "message.send":
            await self._handle_send_message(content)
        elif msg_type == "mark_read":
            await self._handle_mark_read(content)
        elif msg_type == "chat.join":
            await self._handle_chat_join(content)

    # ── Handlers per i messaggi dal client ────────────────────

    async def _handle_send_message(self, content):
        chat_id = content.get("chat_id")
        body = content.get("body", "")

        if not chat_id or not body.strip():
            await self.send_json({"type": "error", "message": "chat_id e body sono obbligatori"})
            return

        if not await self._is_participant(chat_id):
            await self.send_json({"type": "error", "message": "Non sei partecipante di questa chat"})
            return

        # Crea il messaggio nel database
        msg = await self._create_message(chat_id, self.user.id, body)

        # Broadcast a tutti i consumer connessi alla chat
        await self.channel_layer.group_send(
            f"chat_{chat_id}",
            {
                "type": "chat.message",
                "message": msg,
                "chat_id": str(chat_id),
            },
        )

        # Invia aggiornamenti unread a tutti gli altri partecipanti
        participant_ids = await self._get_other_participant_ids(chat_id, self.user.id)
        chat_type = await self._get_chat_type(chat_id)
        for uid in participant_ids:
            unread = await self._get_unread_count_for_user(chat_id, uid)
            await self.channel_layer.group_send(
                f"user_{uid}",
                {
                    "type": "unread.update",
                    "chat_id": str(chat_id),
                    "chat_type": chat_type,
                    "unread_count": unread,
                },
            )

    async def _handle_mark_read(self, content):
        chat_id = content.get("chat_id")
        if not chat_id:
            return

        if not await self._is_participant(chat_id):
            return

        await self._mark_read(chat_id)
        await self.send_json({
            "type": "unread_update",
            "chat_id": str(chat_id),
            "chat_type": await self._get_chat_type(chat_id),
            "unread_count": 0,
        })

    async def _handle_chat_join(self, content):
        """Aggiunge il consumer al gruppo di una nuova chat."""
        chat_id = content.get("chat_id")
        if not chat_id:
            return

        if await self._is_participant(chat_id):
            group_name = f"chat_{chat_id}"
            if group_name not in self.chat_groups:
                self.chat_groups.add(group_name)
                await self.channel_layer.group_add(group_name, self.channel_name)

    # ── Event handlers (dal channel layer) ────────────────────

    async def chat_message(self, event):
        """Nuovo messaggio in una chat — inoltra al client."""
        await self.send_json({
            "type": "new_message",
            "chat_id": event["chat_id"],
            "data": event["message"],
        })

    async def unread_update(self, event):
        """Aggiornamento conteggio non-letti — inoltra al client."""
        await self.send_json({
            "type": "unread_update",
            "chat_id": event["chat_id"],
            "chat_type": event.get("chat_type", ""),
            "unread_count": event["unread_count"],
        })

    # ── DB helpers ────────────────────────────────────────────

    @database_sync_to_async
    def _get_user_chat_ids(self):
        return list(
            ChatParticipant.objects.filter(user_id=self.user.id)
            .values_list("chat_id", flat=True)
        )

    @database_sync_to_async
    def _get_all_unread_counts(self):
        """Restituisce { chat_id: { unread_count, chat_type } } per tutte le chat con messaggi non letti."""
        participants = (
            ChatParticipant.objects.filter(user_id=self.user.id)
            .select_related("chat")
        )
        result = {}
        for part in participants:
            last_read = part.last_read_at or part.joined_at
            count = (
                Message.objects.filter(chat_id=part.chat_id, created_at__gt=last_read)
                .exclude(sender_id=self.user.id)
                .count()
            )
            if count > 0:
                result[str(part.chat_id)] = {
                    "unread_count": count,
                    "chat_type": part.chat.chat_type,
                }
        return result

    @database_sync_to_async
    def _is_participant(self, chat_id):
        return ChatParticipant.objects.filter(
            chat_id=chat_id, user_id=self.user.id
        ).exists()

    @database_sync_to_async
    def _create_message(self, chat_id, user_id, body):
        msg = Message.objects.create(chat_id=chat_id, sender_id=user_id, body=body)
        return {
            "id": msg.id,
            "sender_id": user_id,
            "body": msg.body,
            "created_at": msg.created_at.isoformat(),
            "client_msg_id": str(msg.client_msg_id),
        }

    @database_sync_to_async
    def _get_other_participant_ids(self, chat_id, sender_id):
        return list(
            ChatParticipant.objects.filter(chat_id=chat_id)
            .exclude(user_id=sender_id)
            .values_list("user_id", flat=True)
        )

    @database_sync_to_async
    def _get_chat_type(self, chat_id):
        try:
            return Chat.objects.get(id=chat_id).chat_type
        except Chat.DoesNotExist:
            return ""

    @database_sync_to_async
    def _get_unread_count_for_user(self, chat_id, user_id):
        part = (
            ChatParticipant.objects.filter(chat_id=chat_id, user_id=user_id)
            .only("last_read_at", "joined_at")
            .first()
        )
        if not part:
            return 0
        last_read = part.last_read_at or part.joined_at
        return (
            Message.objects.filter(chat_id=chat_id, created_at__gt=last_read)
            .exclude(sender_id=user_id)
            .count()
        )

    @database_sync_to_async
    def _mark_read(self, chat_id):
        ChatParticipant.objects.filter(
            chat_id=chat_id, user_id=self.user.id
        ).update(last_read_at=timezone.now())