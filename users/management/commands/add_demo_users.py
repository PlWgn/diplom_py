from datetime import date
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from PIL import Image, ImageDraw

from interactions.models import Reaction
from users.models import Hobby, Photo

User = get_user_model()

PASSWORD = 'Demo12345!'

DEMO_USERS = [
    {
        'email': 'anna@demo.ru',
        'first_name': 'Анна',
        'last_name': 'Смирнова',
        'middle_name': 'Сергеевна',
        'gender': User.Gender.FEMALE,
        'birth_date': date(1999, 7, 12),
        'city': 'Москва',
        'status': User.Status.SEARCHING,
        'about': 'Люблю путешествия, кино и долгие прогулки по вечерней '
        'Москве. Ищу человека, с которым будет интересно.',
        'contacts': 'Telegram @anna_demo',
        'hobbies': ['Путешествия', 'Кино', 'Фотография', 'Книги'],
        'colors': [('#ee5c87', '#F3A183'), ('#9198e5', '#e66465')],
    },
    {
        'email': 'ivan@demo.ru',
        'first_name': 'Иван',
        'last_name': 'Петров',
        'middle_name': 'Андреевич',
        'gender': User.Gender.MALE,
        'birth_date': date(1996, 4, 10),
        'city': 'Москва',
        'status': User.Status.OPEN,
        'about': 'Программист, по выходным катаюсь на велосипеде '
        'и играю на гитаре.',
        'contacts': '+7 900 123-45-67',
        'hobbies': ['Спорт', 'Музыка', 'Технологии', 'Автомобили'],
        'colors': [('#26D0CE', '#1A2980'), ('#0575E6', '#021B79')],
    },
]


def make_photo(top_color: str, bottom_color: str):
    width, height = 600, 800
    top = Image.new('RGB', (width, height), top_color)
    bottom = Image.new('RGB', (width, height), bottom_color)
    mask = Image.linear_gradient('L').resize((width, height))
    image = Image.composite(bottom, top, mask)
    draw = ImageDraw.Draw(image)
    draw.ellipse((200, 180, 400, 380), fill='azure')
    draw.ellipse((100, 430, 500, 900), fill='azure')
    file = BytesIO()
    image.save(file, 'JPEG', quality=90)
    return file.getvalue()


class Command(BaseCommand):
    help = 'Добавляет двух демонстрационных пользователей с фотографиями'

    @transaction.atomic
    def handle(self, *args, **options):
        users = []
        for data in DEMO_USERS:
            data = data.copy()
            hobbies = data.pop('hobbies')
            colors = data.pop('colors')
            user = User.objects.filter(email=data['email']).first()
            if user is not None:
                self.stdout.write(f'{data["email"]} уже есть, пропускаем')
                users.append(user)
                continue

            user = User.objects.create_user(password=PASSWORD, **data)
            user.hobbies.set(Hobby.objects.filter(name__in=hobbies))
            for i, (top_color, bottom_color) in enumerate(colors):
                content = make_photo(top_color, bottom_color)
                photo = Photo(user=user, is_main=i == 0)
                photo.image.save(
                    f'demo_{user.pk}_{i}.jpg', ContentFile(content), save=False
                )
                photo.save()
            users.append(user)
            self.stdout.write(f'Добавлен {data["email"]}, пароль {PASSWORD}')

        anna, ivan = users
        Reaction.objects.get_or_create(
            from_user=anna, to_user=ivan, defaults={'is_like': True}
        )
