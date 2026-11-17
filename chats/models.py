from django.conf import settings
from django.db import models


class Message(models.Model):
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='messages_sent',
        verbose_name='Отправитель',
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='messages_received',
        verbose_name='Получатель',
    )
    text = models.TextField('Текст', max_length=1000)
    created_at = models.DateTimeField('Отправлено', auto_now_add=True)

    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
        ordering = ['created_at', 'id']
        indexes = [
            models.Index(
                fields=['sender', 'receiver', 'created_at'],
                name='message_dialog_idx',
            ),
        ]

    def __str__(self):
        return f'{self.sender_id} -> {self.receiver_id}: {self.text[:30]}'
