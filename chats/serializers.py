from django.contrib.auth import get_user_model
from rest_framework import serializers

from interactions.matches import is_match

from .models import Message

User = get_user_model()


class MessageSerializer(serializers.ModelSerializer):
    receiver = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True)
    )

    class Meta:
        model = Message
        fields = ('id', 'sender', 'receiver', 'text', 'created_at')
        read_only_fields = ('sender', 'created_at')

    def validate_text(self, text: str):
        text = text.strip()
        if text == '':
            raise serializers.ValidationError('Сообщение не может быть пустым')
        return text

    def validate_receiver(self, receiver):
        sender = self.context['sender']
        if not is_match(sender.pk, receiver.pk):
            raise serializers.ValidationError(
                'Писать можно только при взаимной симпатии'
            )
        return receiver
