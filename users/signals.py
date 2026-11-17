from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Photo


@receiver(post_delete, sender=Photo)
def delete_photo_file(sender, instance: Photo, **kwargs):
    if instance.image:
        instance.image.delete(save=False)
    if not instance.is_main:
        return
    next_photo = Photo.objects.filter(user_id=instance.user_id).first()
    if next_photo is not None:
        next_photo.make_main()
