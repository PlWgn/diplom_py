from django.contrib.auth import get_user_model
from django.db.models import Q
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from .filters import InviteFilter, ReactionFilter
from .matches import get_exchanged_ids
from .models import Invite, ProfileView, Reaction
from .serializers import (
    InviteAnswerSerializer,
    InviteSerializer,
    MatchSerializer,
    ProfileViewSerializer,
    ReactionResultSerializer,
    ReactionSerializer,
    ReceivedLikeSerializer,
)

User = get_user_model()


@extend_schema_view(
    list=extend_schema(
        summary='Мои лайки и дизлайки',
        description='is_like=true - понравившиеся, false - непонравившиеся',
    ),
)
class ReactionViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Reaction.objects.none()
    filterset_class = ReactionFilter

    def get_queryset(self):
        if self.action == 'received':
            return (
                Reaction.objects.filter(
                    to_user=self.request.user, is_like=True
                )
                .select_related('from_user')
                .prefetch_related('from_user__photos')
            )
        return (
            Reaction.objects.filter(from_user=self.request.user)
            .select_related('to_user')
            .prefetch_related('to_user__photos')
        )

    def get_serializer_class(self):
        if self.action == 'create':
            return ReactionResultSerializer
        if self.action == 'received':
            return ReceivedLikeSerializer
        return ReactionSerializer

    @extend_schema(
        summary='Поставить лайк или дизлайк',
        description=(
            'Если анкета уже оценена, оценка меняется (ответ 200), '
            'иначе создается новая (ответ 201). '
            'is_match - есть ли взаимная симпатия.'
        ),
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reaction = serializer.save(from_user=request.user)
        if reaction.is_created:
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(summary='История лайков моей анкеты')
    @action(detail=False, filter_backends=[])
    def received(self, request):
        return super().list(request)


@extend_schema_view(
    list=extend_schema(summary='История просмотренных анкет'),
)
class ProfileViewViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ProfileView.objects.none()
    serializer_class = ProfileViewSerializer

    def get_queryset(self):
        return (
            ProfileView.objects.filter(viewer=self.request.user)
            .select_related('viewed')
            .prefetch_related('viewed__photos')
        )


@extend_schema_view(
    list=extend_schema(
        summary='Взаимные симпатии',
        description='Контакты видны после принятого приглашения',
    ),
)
class MatchViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = User.objects.none()
    serializer_class = MatchSerializer

    def get_queryset(self):
        user = self.request.user
        return (
            User.objects.filter(
                reactions_sent__to_user=user,
                reactions_sent__is_like=True,
                reactions_received__from_user=user,
                reactions_received__is_like=True,
            )
            .prefetch_related('photos')
            .order_by('-reactions_received__updated_at')
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['exchanged_ids'] = get_exchanged_ids(self.request.user.pk)
        return context


@extend_schema_view(
    create=extend_schema(
        summary='Пригласить на свидание или обменяться контактами',
        description='Только при взаимной симпатии',
    ),
    partial_update=extend_schema(
        summary='Ответить на приглашение',
        description='Только получатель, status accepted или declined',
    ),
    destroy=extend_schema(
        summary='Отменить приглашение',
        description='Только отправитель, пока нет ответа',
    ),
)
class InviteViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Invite.objects.none()
    filterset_class = InviteFilter
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        user = self.request.user
        return (
            Invite.objects.filter(Q(sender=user) | Q(receiver=user))
            .select_related('sender', 'receiver')
            .prefetch_related('sender__photos', 'receiver__photos')
        )

    def get_serializer_class(self):
        if self.action == 'partial_update':
            return InviteAnswerSerializer
        return InviteSerializer

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)

    def perform_update(self, serializer):
        if serializer.instance.receiver != self.request.user:
            raise PermissionDenied('Ответить может только получатель')
        serializer.save()

    def perform_destroy(self, invite: Invite):
        if invite.sender != self.request.user:
            raise PermissionDenied('Отменить может только отправитель')
        if invite.status != Invite.Status.PENDING:
            raise PermissionDenied('На приглашение уже ответили')
        invite.delete()
