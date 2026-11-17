import re

from django.core.exceptions import ValidationError
from django.utils import timezone

MIN_AGE = 18
MAX_AGE = 100
MAX_PHOTO_SIZE_MB = 5
MAX_PHOTOS_COUNT = 10

NAME_REGEX = re.compile(r'^[A-Za-zА-Яа-яЁё]+([ -][A-Za-zА-Яа-яЁё]+)*$')


def get_age(birth_date) -> int:
    today = timezone.localdate()
    is_birthday_passed = (today.month, today.day) >= (
        birth_date.month,
        birth_date.day,
    )
    return today.year - birth_date.year - (0 if is_birthday_passed else 1)


def validate_birth_date(birth_date):
    age = get_age(birth_date)
    if age < MIN_AGE:
        raise ValidationError(f'Регистрация доступна только с {MIN_AGE} лет')
    if age > MAX_AGE:
        raise ValidationError('Проверьте дату рождения')


def validate_name(name: str):
    if not NAME_REGEX.match(name):
        raise ValidationError(
            'Можно использовать только буквы, пробел и дефис'
        )


def validate_photo_size(image):
    if image.size > MAX_PHOTO_SIZE_MB * 1024 * 1024:
        raise ValidationError(
            f'Размер фотографии не должен превышать {MAX_PHOTO_SIZE_MB} МБ'
        )
