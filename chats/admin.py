from django.contrib import admin

from .models import Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'receiver', 'text', 'created_at')
    list_select_related = ('sender', 'receiver')
    autocomplete_fields = ('sender', 'receiver')
