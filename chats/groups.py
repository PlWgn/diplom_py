from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def get_group_name(user_id: int, other_id: int) -> str:
    first_id, second_id = sorted([int(user_id), int(other_id)])
    return f'chat_{first_id}_{second_id}'


def send_to_chat(message_data: dict):
    async_to_sync(get_channel_layer().group_send)(
        get_group_name(message_data['sender'], message_data['receiver']),
        {'type': 'chat.message', 'message': message_data},
    )
