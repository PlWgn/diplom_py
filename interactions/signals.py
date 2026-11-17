from django.contrib.auth import get_user_model
from django.db.models import F
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .models import Reaction

User = get_user_model()


def change_likes_count(user_id: int, delta: int):
    User.objects.filter(pk=user_id).update(
        likes_count=F('likes_count') + delta
    )


@receiver(pre_save, sender=Reaction)
def remember_old_reaction(sender, instance: Reaction, **kwargs):
    instance.old_is_like = None
    if instance.pk is not None:
        instance.old_is_like = (
            Reaction.objects.filter(pk=instance.pk)
            .values_list('is_like', flat=True)
            .first()
        )


@receiver(post_save, sender=Reaction)
def update_likes_count(sender, instance: Reaction, created: bool, **kwargs):
    if created:
        if instance.is_like:
            change_likes_count(instance.to_user_id, 1)
        return
    if (
        instance.old_is_like is None
        or instance.old_is_like == instance.is_like
    ):
        return
    change_likes_count(instance.to_user_id, 1 if instance.is_like else -1)


@receiver(post_delete, sender=Reaction)
def decrease_likes_count(sender, instance: Reaction, **kwargs):
    if instance.is_like:
        change_likes_count(instance.to_user_id, -1)
