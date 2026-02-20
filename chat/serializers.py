"""
Serializers for the Customer Support Chat API.
"""

from rest_framework import serializers
from .models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for Message model."""

    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender_type', 'sender_name',
            'sender_avatar', 'content', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class MessageCreateSerializer(serializers.Serializer):
    """Serializer for creating a new message."""
    content = serializers.CharField()


class ConversationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing conversations."""
    last_message_preview = serializers.SerializerMethodField()
    last_message_at = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id', 'customer_name', 'customer_avatar',
            'last_message_preview', 'last_message_at',
            'status', 'unread_count', 'is_pinned',
        ]

    def get_last_message_preview(self, obj):
        msg = obj.messages.order_by('-created_at').first()
        if msg:
            return msg.content[:100]
        return ''

    def get_last_message_at(self, obj):
        msg = obj.messages.order_by('-created_at').first()
        if msg:
            return msg.created_at.isoformat()
        return obj.created_at.isoformat()

    def get_unread_count(self, obj):
        return obj.messages.filter(sender_type='customer', is_read=False).count()


class ConversationDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer with all messages."""
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = [
            'id', 'customer_name', 'customer_avatar', 'customer_phone',
            'is_pinned', 'status', 'messages', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
