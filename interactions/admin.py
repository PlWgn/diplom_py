from django.contrib import admin

from .models import Invite, ProfileView, Reaction


@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'from_user', 'to_user', 'is_like', 'updated_at')
    list_filter = ('is_like',)
    list_select_related = ('from_user', 'to_user')
    autocomplete_fields = ('from_user', 'to_user')


@admin.register(ProfileView)
class ProfileViewAdmin(admin.ModelAdmin):
    list_display = ('id', 'viewer', 'viewed', 'viewed_at')
    list_select_related = ('viewer', 'viewed')
    autocomplete_fields = ('viewer', 'viewed')


@admin.register(Invite)
class InviteAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'receiver', 'kind', 'status', 'created_at')
    list_filter = ('kind', 'status')
    list_select_related = ('sender', 'receiver')
    autocomplete_fields = ('sender', 'receiver')
