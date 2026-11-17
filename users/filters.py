from django.contrib.auth import get_user_model
from django.utils import timezone
from django_filters import rest_framework as filters

from .validators import MAX_AGE, MIN_AGE

User = get_user_model()


def get_years_ago(years: int):
    today = timezone.localdate()
    try:
        return today.replace(year=today.year - years)
    except ValueError:
        return today.replace(year=today.year - years, day=28)


class UserFilter(filters.FilterSet):
    city = filters.CharFilter(lookup_expr='iexact', label='Город')
    age_min = filters.NumberFilter(
        method='filter_age_min',
        label='Возраст от',
        min_value=MIN_AGE,
        max_value=MAX_AGE,
    )
    age_max = filters.NumberFilter(
        method='filter_age_max',
        label='Возраст до',
        min_value=MIN_AGE,
        max_value=MAX_AGE,
    )
    hobby = filters.NumberFilter(field_name='hobbies', label='Id увлечения')

    class Meta:
        model = User
        fields = ('gender', 'status', 'city', 'age_min', 'age_max', 'hobby')

    def filter_age_min(self, queryset, name: str, value):
        return queryset.filter(birth_date__lte=get_years_ago(int(value)))

    def filter_age_max(self, queryset, name: str, value):
        return queryset.filter(birth_date__gt=get_years_ago(int(value) + 1))
