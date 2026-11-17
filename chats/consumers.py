from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth import get_user_model

from interactions.matches import is_match

from .groups import get_group_name
from .serializers import MessageSerializer

User = get_user_model()


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        self.other_id = int(self.scope['url_route']['kwargs']['user_id'])
        if not self.user.is_authenticated:
            await self.close(code=4401)
            return
        if not await database_sync_to_async(is_match)(
            self.user.pk, self.other_id
        ):
            await self.close(code=4403)
            return
        self.group_name = get_group_name(self.user.pk, self.other_id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code: int):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name, self.channel_name
            )

    async def receive_json(self, content: dict, **kwargs):
        data, errors = await self.save_message(content.get('text', ''))
        if errors:
            await self.send_json({'errors': errors})
            return
        await self.channel_layer.group_send(
            self.group_name, {'type': 'chat.message', 'message': data}
        )

    async def chat_message(self, event: dict):
        await self.send_json(event['message'])

    @database_sync_to_async
    def save_message(self, text: str):
        serializer = MessageSerializer(
            data={'receiver': self.other_id, 'text': text},
            context={'sender': self.user},
        )
        if not serializer.is_valid():
            return None, serializer.errors
        serializer.save(sender=self.user)
        return serializer.data, None
