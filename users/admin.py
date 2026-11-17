from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Hobby, Photo, User


class PhotoInline(admin.TabularInline):
    model = Photo
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ('id',)
    list_display = (
        'id',
        'email',
        'last_name',
        'first_name',
        'gender',
        'city',
        'status',
        'likes_count',
    )
    list_display_links = ('id', 'email')
    list_filter = ('gender', 'status', 'is_visible', 'is_staff')
    search_fields = ('email', 'last_name', 'first_name', 'city')
    readonly_fields = ('likes_count', 'last_login', 'date_joined')
    filter_horizontal = ('hobbies', 'groups', 'user_permissions')
    inlines = [PhotoInline]
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (
            'Анкета',
            {
                'fields': (
                    'last_name',
                    'first_name',
                    'middle_name',
                    'gender',
                    'birth_date',
                    'city',
                    'hobbies',
                    'about',
                    'status',
                    'contacts',
                    'likes_count',
                )
            },
        ),
        (
            'Приватность',
            {
                'fields': (
                    'is_visible',
                    'is_age_hidden',
                    'is_likes_hidden',
                    'is_full_name_hidden',
                )
            },
        ),
        (
            'Права доступа',
            {
                'fields': (
                    'is_active',
                    'is_staff',
                    'is_superuser',
                    'groups',
                    'user_permissions',
                )
            },
        ),
        ('Даты', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': (
                    'email',
                    'first_name',
                    'last_name',
                    'password1',
                    'password2',
                ),
            },
        ),
    )


@admin.register(Hobby)
class HobbyAdmin(admin.ModelAdmin):
    search_fields = ('name',)


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'is_main', 'created_at')
    list_select_related = ('user',)
    autocomplete_fields = ('user',)
