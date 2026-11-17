from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import FileExtensionValidator
from django.db import models, transaction

from .validators import (
    get_age,
    validate_birth_date,
    validate_name,
    validate_photo_size,
)


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email: str, password: str = None, **extra_fields):
        if not email:
            raise ValueError('Не указан email')
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str, **extra_fields):
        extra_fields['is_staff'] = True
        extra_fields['is_superuser'] = True
        extra_fields.setdefault('is_visible', False)
        return self.create_user(email, password, **extra_fields)


class Hobby(models.Model):
    name = models.CharField('Название', max_length=50, unique=True)

    class Meta:
        verbose_name = 'Увлечение'
        verbose_name_plural = 'Увлечения'
        ordering = ['name']

    def __str__(self):
        return self.name


class User(AbstractUser):
    class Gender(models.TextChoices):
        MALE = 'm', 'Мужской'
        FEMALE = 'f', 'Женский'

    class Status(models.TextChoices):
        SEARCHING = 'searching', 'В поиске'
        OPEN = 'open', 'Открыт(а) к общению'
        BUSY = 'busy', 'Занят(а)'

    username = None
    email = models.EmailField('Email', unique=True)
    first_name = models.CharField(
        'Имя', max_length=50, validators=[validate_name]
    )
    last_name = models.CharField(
        'Фамилия', max_length=50, validators=[validate_name]
    )
    middle_name = models.CharField(
        'Отчество', max_length=50, blank=True, validators=[validate_name]
    )
    gender = models.CharField(
        'Пол', max_length=1, choices=Gender.choices, blank=True
    )
    birth_date = models.DateField(
        'Дата рождения',
        null=True,
        blank=True,
        validators=[validate_birth_date],
    )
    city = models.CharField(
        'Город', max_length=100, blank=True, validators=[validate_name]
    )
    hobbies = models.ManyToManyField(
        Hobby, blank=True, related_name='users', verbose_name='Увлечения'
    )
    about = models.TextField('О себе', max_length=1000, blank=True)
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=Status.choices,
        default=Status.SEARCHING,
    )
    contacts = models.CharField(
        'Контакты',
        max_length=200,
        blank=True,
        help_text='Видны только после принятого приглашения',
    )
    likes_count = models.PositiveIntegerField(
        'Количество лайков', default=0, editable=False
    )
    is_visible = models.BooleanField(
        'Показывать анкету в поиске', default=True
    )
    is_age_hidden = models.BooleanField('Скрыть возраст', default=False)
    is_likes_hidden = models.BooleanField(
        'Скрыть количество лайков', default=False
    )
    is_full_name_hidden = models.BooleanField(
        'Показывать только имя', default=False
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['id']
        indexes = [
            models.Index(
                fields=['gender', 'status', 'birth_date'],
                name='user_search_idx',
            ),
            models.Index(fields=['city'], name='user_city_idx'),
        ]

    def __str__(self):
        return f'{self.get_full_name()} ({self.email})'

    def get_full_name(self):
        return ' '.join(
            name
            for name in [self.last_name, self.first_name, self.middle_name]
            if name
        )

    @property
    def age(self):
        if self.birth_date is None:
            return None
        return get_age(self.birth_date)


class Photo(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='photos',
        verbose_name='Пользователь',
    )
    image = models.ImageField(
        'Фотография',
        upload_to='photos/%Y/%m/',
        validators=[
            FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp']),
            validate_photo_size,
        ],
    )
    is_main = models.BooleanField('Заглавная', default=False)
    created_at = models.DateTimeField('Загружена', auto_now_add=True)

    class Meta:
        verbose_name = 'Фотография'
        verbose_name_plural = 'Фотографии'
        ordering = ['-is_main', 'created_at', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                condition=models.Q(is_main=True),
                name='one_main_photo_per_user',
            ),
        ]

    def __str__(self):
        return f'Фото {self.pk} пользователя {self.user_id}'

    @transaction.atomic
    def make_main(self):
        Photo.objects.filter(user_id=self.user_id, is_main=True).exclude(
            pk=self.pk
        ).update(is_main=False)
        self.is_main = True
        self.save(update_fields=['is_main'])
