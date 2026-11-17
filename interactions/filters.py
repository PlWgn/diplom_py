from django_filters import rest_framework as filters

from .models import Invite, Reaction


class ReactionFilter(filters.FilterSet):
    class Meta:
        model = Reaction
        fields = ('is_like',)


class InviteFilter(filters.FilterSet):
    direction = filters.ChoiceFilter(
        method='filter_direction',
        choices=[('incoming', 'Входящие'), ('outgoing', 'Исходящие')],
        label='Входящие или исходящие',
    )

    class Meta:
        model = Invite
        fields = ('direction', 'kind', 'status')

    def filter_direction(self, queryset, name: str, value: str):
        user = self.request.user
        if value == 'incoming':
            return queryset.filter(receiver=user)
        return queryset.filter(sender=user)
