from django.conf import settings
from django.db import models
from django.db.models import Q

from .validators import validate_future_datetime


class Reaction(models.Model):
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reactions_sent',
        verbose_name='Кто оценил',
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reactions_received',
        verbose_name='Кого оценили',
    )
    is_like = models.BooleanField('Лайк', help_text='False - дизлайк')
    created_at = models.DateTimeField('Создана', auto_now_add=True)
    updated_at = models.DateTimeField('Изменена', auto_now=True)

    class Meta:
        verbose_name = 'Лайк/дизлайк'
        verbose_name_plural = 'Лайки и дизлайки'
        ordering = ['-updated_at', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['from_user', 'to_user'], name='unique_reaction'
            ),
            models.CheckConstraint(
                condition=~Q(from_user=models.F('to_user')),
                name='no_self_reaction',
            ),
        ]
        indexes = [
            models.Index(
                fields=['to_user', 'is_like'], name='reaction_received_idx'
            ),
            models.Index(
                fields=['from_user', 'is_like'], name='reaction_sent_idx'
            ),
        ]

    def __str__(self):
        reaction = 'лайк' if self.is_like else 'дизлайк'
        return f'{self.from_user_id} -> {self.to_user_id}: {reaction}'


class ProfileView(models.Model):
    viewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='views_made',
        verbose_name='Кто смотрел',
    )
    viewed = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='views_received',
        verbose_name='Чью анкету смотрели',
    )
    viewed_at = models.DateTimeField('Последний просмотр', auto_now=True)

    class Meta:
        verbose_name = 'Просмотр анкеты'
        verbose_name_plural = 'История просмотров'
        ordering = ['-viewed_at', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['viewer', 'viewed'], name='unique_profile_view'
            ),
        ]

    def __str__(self):
        return f'{self.viewer_id} смотрел(а) {self.viewed_id}'


class Invite(models.Model):
    class Kind(models.TextChoices):
        DATE = 'date', 'Приглашение на свидание'
        CONTACTS = 'contacts', 'Обмен контактами'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Ожидает ответа'
        ACCEPTED = 'accepted', 'Принято'
        DECLINED = 'declined', 'Отклонено'

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='invites_sent',
        verbose_name='Отправитель',
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='invites_received',
        verbose_name='Получатель',
    )
    kind = models.CharField('Тип', max_length=10, choices=Kind.choices)
    message = models.CharField('Сообщение', max_length=500, blank=True)
    date_time = models.DateTimeField(
        'Дата и время свидания',
        null=True,
        blank=True,
        validators=[validate_future_datetime],
    )
    place = models.CharField('Место свидания', max_length=200, blank=True)
    status = models.CharField(
        'Статус',
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField('Отправлено', auto_now_add=True)

    class Meta:
        verbose_name = 'Приглашение'
        verbose_name_plural = 'Приглашения'
        ordering = ['-created_at', '-id']
        constraints = [
            models.CheckConstraint(
                condition=~Q(sender=models.F('receiver')),
                name='no_self_invite',
            ),
        ]

    def __str__(self):
        return (
            f'{self.get_kind_display()}: {self.sender_id} -> '
            f'{self.receiver_id}'
        )
