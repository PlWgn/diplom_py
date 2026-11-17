from datetime import date
from http import HTTPStatus

from asgiref.sync import async_to_sync, sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from dating.asgi import application
from interactions.models import Reaction

from .models import Message

User = get_user_model()


def make_users():
    users = [
        User.objects.create_user(
            f'{name}@mail.ru',
            'Pass12345!',
            first_name='Тест',
            last_name='Тестов',
            birth_date=date(2000, 1, 1),
        )
        for name in ['ivan', 'anna', 'olga']
    ]
    ivan, anna, olga = users
    Reaction.objects.create(from_user=ivan, to_user=anna, is_like=True)
    Reaction.objects.create(from_user=anna, to_user=ivan, is_like=True)
    Reaction.objects.create(from_user=ivan, to_user=olga, is_like=True)
    return users


class MessageApiTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ivan, cls.anna, cls.olga = make_users()

    def setUp(self):
        self.url = reverse('message-list')
        self.client.force_authenticate(self.ivan)

    def send(self, user, text: str = 'Привет!'):
        return self.client.post(
            self.url, {'receiver': user.pk, 'text': text}, format='json'
        )

    def test_send_only_to_match(self):
        self.assertEqual(self.send(self.anna).status_code, HTTPStatus.CREATED)
        response = self.send(self.olga)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertIn('receiver', response.data)
        self.assertEqual(
            self.send(self.anna, '   ').status_code, HTTPStatus.BAD_REQUEST
        )

    def test_dialog_history(self):
        self.send(self.anna, 'Привет!')
        Message.objects.create(sender=self.anna, receiver=self.ivan, text='Ку')
        Message.objects.create(sender=self.anna, receiver=self.olga, text='?')
        response = self.client.get(self.url, {'user': self.anna.pk})
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['results'][0]['text'], 'Ку')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.client.force_authenticate(self.olga)
        response = self.client.get(self.url, {'user': self.ivan.pk})
        self.assertEqual(response.data['count'], 0)


class ChatWebSocketTest(TransactionTestCase):
    def setUp(self):
        self.ivan, self.anna, self.olga = make_users()

    def get_communicator(self, user, other):
        token = AccessToken.for_user(user) if user else 'wrong'
        return WebsocketCommunicator(
            application,
            f'/ws/chat/{other.pk}/?token={token}',
            headers=[(b'origin', b'http://localhost')],
        )

    @async_to_sync
    async def check_chat(self):
        ivan_chat = self.get_communicator(self.ivan, self.anna)
        anna_chat = self.get_communicator(self.anna, self.ivan)
        is_connected, code = await ivan_chat.connect()
        self.assertTrue(is_connected)
        is_connected, code = await anna_chat.connect()
        self.assertTrue(is_connected)
        await ivan_chat.send_json_to({'text': 'Привет, Анна!'})
        message = await anna_chat.receive_json_from()
        self.assertEqual(message['text'], 'Привет, Анна!')
        self.assertEqual(message['sender'], self.ivan.pk)
        self.assertEqual(
            (await ivan_chat.receive_json_from())['text'], 'Привет, Анна!'
        )
        await ivan_chat.send_json_to({'text': ''})
        self.assertIn('errors', await ivan_chat.receive_json_from())
        await ivan_chat.disconnect()
        await anna_chat.disconnect()

    @async_to_sync
    async def check_rejected(self, user, other, close_code: int):
        communicator = self.get_communicator(user, other)
        is_connected, code = await communicator.connect()
        self.assertFalse(is_connected)
        self.assertEqual(code, close_code)

    def test_chat_between_match(self):
        self.check_chat()
        self.assertEqual(Message.objects.count(), 1)

    def test_rejected_without_match_or_token(self):
        self.check_rejected(self.ivan, self.olga, 4403)
        self.check_rejected(None, self.anna, 4401)

    @async_to_sync
    async def check_rest_message(self):
        communicator = self.get_communicator(self.anna, self.ivan)
        await communicator.connect()
        client = APIClient()
        client.force_authenticate(self.ivan)
        await sync_to_async(client.post)(
            reverse('message-list'),
            {'receiver': self.anna.pk, 'text': 'Из REST'},
            format='json',
        )
        message = await communicator.receive_json_from()
        self.assertEqual(message['text'], 'Из REST')
        await communicator.disconnect()

    def test_rest_message_comes_to_websocket(self):
        self.check_rest_message()
