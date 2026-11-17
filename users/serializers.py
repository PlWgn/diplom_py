from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Hobby, Photo
from .validators import MAX_PHOTOS_COUNT

User = get_user_model()


def get_photo_url(photo: Photo, request) -> str:
    if request is None:
        return photo.image.url
    return request.build_absolute_uri(photo.image.url)


class HobbySerializer(serializers.ModelSerializer):
    class Meta:
        model = Hobby
        fields = ('id', 'name')


class PhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Photo
        fields = ('id', 'image', 'is_main', 'created_at')
        read_only_fields = ('is_main', 'created_at')

    def validate(self, data: dict):
        user = self.context['request'].user
        if user.photos.count() >= MAX_PHOTOS_COUNT:
            raise serializers.ValidationError(
                f'Можно загрузить не больше {MAX_PHOTOS_COUNT} фотографий'
            )
        return data


class PhotoMainSerializer(serializers.ModelSerializer):
    class Meta:
        model = Photo
        fields = ('id', 'image', 'is_main', 'created_at')
        read_only_fields = ('image', 'created_at')

    def validate_is_main(self, is_main: bool):
        if not is_main:
            raise serializers.ValidationError(
                'Выберите заглавной другую фотографию, '
                'тогда эта перестанет быть заглавной'
            )
        return is_main

    def update(self, photo: Photo, validated_data: dict):
        photo.make_main()
        return photo


class ShortProfileSerializer(serializers.ModelSerializer):
    age = serializers.IntegerField(read_only=True, allow_null=True)
    main_photo = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'first_name', 'age', 'city', 'status', 'main_photo')

    def get_main_photo(self, user) -> str:
        photos = user.photos.all()
        if len(photos) == 0:
            return None
        return get_photo_url(photos[0], self.context.get('request'))

    def to_representation(self, user):
        data = super().to_representation(user)
        if user.is_age_hidden:
            data['age'] = None
        if user.is_full_name_hidden:
            for field in ('last_name', 'middle_name', 'full_name'):
                if field in data:
                    data[field] = None
        if user.is_likes_hidden and 'likes_count' in data:
            data['likes_count'] = None
        if 'contacts' in data:
            exchanged_ids = self.context.get('exchanged_ids', set())
            if user.id not in exchanged_ids:
                data['contacts'] = None
        return data


class ProfileSerializer(ShortProfileSerializer):
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    gender_display = serializers.CharField(
        source='get_gender_display', read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    hobbies = HobbySerializer(many=True, read_only=True)
    photos = PhotoSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = (
            'id',
            'full_name',
            'first_name',
            'last_name',
            'middle_name',
            'gender',
            'gender_display',
            'age',
            'city',
            'hobbies',
            'about',
            'status',
            'status_display',
            'likes_count',
            'main_photo',
            'photos',
            'contacts',
        )
        read_only_fields = fields


class MyProfileSerializer(ProfileSerializer):
    hobby_ids = serializers.PrimaryKeyRelatedField(
        source='hobbies',
        queryset=Hobby.objects.all(),
        many=True,
        write_only=True,
        required=False,
    )

    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'full_name',
            'first_name',
            'last_name',
            'middle_name',
            'gender',
            'gender_display',
            'birth_date',
            'age',
            'city',
            'hobbies',
            'hobby_ids',
            'about',
            'status',
            'status_display',
            'contacts',
            'likes_count',
            'main_photo',
            'photos',
            'is_visible',
            'is_age_hidden',
            'is_likes_hidden',
            'is_full_name_hidden',
        )
        read_only_fields = ('email', 'likes_count')

    def to_representation(self, user):
        return super(ShortProfileSerializer, self).to_representation(user)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'password',
            'first_name',
            'last_name',
            'middle_name',
            'gender',
            'birth_date',
            'city',
        )
        extra_kwargs = {
            'gender': {'required': True, 'allow_blank': False},
            'birth_date': {'required': True, 'allow_null': False},
            'city': {'required': True, 'allow_blank': False},
        }

    def validate_email(self, email: str):
        email = email.lower()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError(
                'Пользователь с таким email уже зарегистрирован'
            )
        return email

    def validate(self, data: dict):
        user_data = data.copy()
        password = user_data.pop('password')
        try:
            validate_password(password, User(**user_data))
        except DjangoValidationError as err:
            raise serializers.ValidationError({'password': err.messages})
        return data

    def create(self, validated_data: dict):
        return User.objects.create_user(**validated_data)
