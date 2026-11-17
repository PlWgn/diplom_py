import random

from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from interactions.matches import get_exchanged_ids
from interactions.models import ProfileView

from .filters import UserFilter
from .models import Hobby, Photo
from .serializers import (
    HobbySerializer,
    MyProfileSerializer,
    PhotoMainSerializer,
    PhotoSerializer,
    ProfileSerializer,
    RegisterSerializer,
    ShortProfileSerializer,
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []


class HobbyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Hobby.objects.all()
    serializer_class = HobbySerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None


class UserViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    filterset_class = UserFilter

    def get_queryset(self):
        queryset = User.objects.prefetch_related('photos')
        if self.action == 'me':
            return queryset.prefetch_related('hobbies')
        queryset = queryset.filter(
            is_active=True, birth_date__isnull=False
        ).exclude(pk=self.request.user.pk)
        if self.action == 'list':
            return queryset.filter(is_visible=True)
        if self.action == 'random':
            return queryset.filter(is_visible=True).exclude(
                reactions_received__from_user=self.request.user
            )
        return queryset.prefetch_related('hobbies')

    def get_serializer_class(self):
        if self.action == 'list':
            return ShortProfileSerializer
        if self.action == 'me':
            return MyProfileSerializer
        return ProfileSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.action in ('retrieve', 'random'):
            context['exchanged_ids'] = get_exchanged_ids(self.request.user.pk)
        return context

    def save_view(self, user):
        ProfileView.objects.update_or_create(
            viewer=self.request.user, viewed=user
        )

    def retrieve(self, request, *args, **kwargs):
        user = self.get_object()
        self.save_view(user)
        return Response(self.get_serializer(user).data)

    @extend_schema(
        summary='Случайная анкета',
        description=(
            'Случайная анкета с учетом фильтров. Свои и уже оцененные '
            'анкеты не показываются. Просмотр сохраняется в историю.'
        ),
        responses={200: ProfileSerializer},
    )
    @action(detail=False)
    def random(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        users_count = queryset.count()
        if users_count == 0:
            return Response(
                {'detail': 'Подходящих анкет не найдено'},
                status=status.HTTP_404_NOT_FOUND,
            )
        user = queryset.prefetch_related('hobbies')[
            random.randrange(users_count)
        ]
        self.save_view(user)
        return Response(self.get_serializer(user).data)

    @extend_schema(summary='Мой профиль')
    @action(
        detail=False,
        methods=['get', 'put', 'patch', 'delete'],
        filter_backends=[],
        pagination_class=None,
    )
    def me(self, request):
        user = self.get_queryset().get(pk=request.user.pk)
        if request.method == 'GET':
            return Response(self.get_serializer(user).data)
        if request.method == 'DELETE':
            user.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        serializer = self.get_serializer(
            user, data=request.data, partial=request.method == 'PATCH'
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        user = self.get_queryset().get(pk=request.user.pk)
        return Response(self.get_serializer(user).data)


@extend_schema_view(
    partial_update=extend_schema(summary='Сделать фотографию заглавной'),
)
class PhotoViewSet(viewsets.ModelViewSet):
    queryset = Photo.objects.none()
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    pagination_class = None
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return Photo.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == 'partial_update':
            return PhotoMainSerializer
        return PhotoSerializer

    def perform_create(self, serializer):
        is_first = not Photo.objects.filter(user=self.request.user).exists()
        serializer.save(user=self.request.user, is_main=is_first)
