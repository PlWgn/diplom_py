from django.db.models import Q
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, viewsets

from .groups import send_to_chat
from .models import Message
from .serializers import MessageSerializer


class MessageFilter(filters.FilterSet):
    user = filters.NumberFilter(
        method='filter_dialog', required=True, label='Id собеседника'
    )

    class Meta:
        model = Message
        fields = ('user',)

    def filter_dialog(self, queryset, name: str, value):
        return queryset.filter(Q(sender_id=value) | Q(receiver_id=value))


@extend_schema_view(
    list=extend_schema(
        summary='История переписки, новые сообщения первыми',
        description=(
            'Новые сообщения приходят через WebSocket '
            'ws://<host>/ws/chat/<id собеседника>/?token=<access>'
        ),
    ),
)
class MessageViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet
):
    queryset = Message.objects.none()
    serializer_class = MessageSerializer
    filterset_class = MessageFilter

    def get_queryset(self):
        user = self.request.user
        return Message.objects.filter(
            Q(sender=user) | Q(receiver=user)
        ).order_by('-created_at', '-id')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['sender'] = self.request.user
        return context

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)
        send_to_chat(serializer.data)
