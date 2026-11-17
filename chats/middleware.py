from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()


@database_sync_to_async
def get_user(token: str):
    try:
        user_id = AccessToken(token)['user_id']
    except (TokenError, KeyError):
        return AnonymousUser()
    return User.objects.filter(pk=user_id, is_active=True).first() or (
        AnonymousUser()
    )


class JWTAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        query = parse_qs(scope['query_string'].decode())
        token = query.get('token', [''])[0]
        scope['user'] = await get_user(token)
        return await self.app(scope, receive, send)
