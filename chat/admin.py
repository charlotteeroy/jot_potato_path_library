from django.contrib import admin
from .models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ['id', 'created_at']


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['customer_name', 'status', 'customer_phone', 'created_at', 'updated_at']
    list_filter = ['status']
    search_fields = ['customer_name', 'customer_phone']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['sender_name', 'sender_type', 'content_preview', 'conversation', 'created_at']
    list_filter = ['sender_type']
    search_fields = ['content', 'sender_name']
    readonly_fields = ['id', 'created_at', 'updated_at']

    def content_preview(self, obj):
        return obj.content[:80]
    content_preview.short_description = 'Content'
