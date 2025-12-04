from django.contrib import admin
from .models import Chat, Message, ChatParticipant, MessageTranslation


class ChatParticipantInline(admin.TabularInline):
    model = ChatParticipant
    extra = 1
    raw_id_fields = ['user']


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ['id', 'chat_type', 'name', 'created_by', 'participant_count', 'created_at']
    list_filter = ['chat_type', 'created_at']
    search_fields = ['name', 'id']
    readonly_fields = ['id', 'created_at']
    inlines = [ChatParticipantInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by').prefetch_related('participants')
    
    def participant_count(self, obj):
        return obj.participants.count()
    participant_count.short_description = 'Partecipanti'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'chat', 'sender', 'body_preview', 'created_at']
    list_filter = ['created_at']
    search_fields = ['body', 'sender__username']
    readonly_fields = ['id', 'created_at', 'client_msg_id']
    raw_id_fields = ['chat', 'sender']
    
    def body_preview(self, obj):
        return obj.body[:50] + '...' if len(obj.body) > 50 else obj.body
    body_preview.short_description = 'Body'


@admin.register(ChatParticipant)
class ChatParticipantAdmin(admin.ModelAdmin):
    list_display = ['chat', 'user', 'role', 'joined_at']
    list_filter = ['role', 'joined_at']
    search_fields = ['user__username', 'chat__name']
    readonly_fields = ['joined_at']
    raw_id_fields = ['chat', 'user']


@admin.register(MessageTranslation)
class MessageTranslationAdmin(admin.ModelAdmin):
    list_display = ['message', 'target_language', 'provider', 'created_at']
    search_fields = ['message__body', 'target_language']
    list_filter = ['provider', 'target_language', 'created_at']
    readonly_fields = ['created_at']
    raw_id_fields = ['message']
