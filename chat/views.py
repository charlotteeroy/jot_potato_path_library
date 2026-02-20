"""
API Views for the Customer Support Chat.
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Conversation, Message, ConversationStatus
from .serializers import (
    ConversationListSerializer,
    ConversationDetailSerializer,
    MessageSerializer,
    MessageCreateSerializer,
)


class ConversationViewSet(viewsets.ModelViewSet):
    """API endpoint for Conversations."""
    queryset = Conversation.objects.prefetch_related('messages')
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status']
    search_fields = ['customer_name']
    ordering_fields = ['updated_at', 'created_at']
    ordering = ['-is_pinned', '-updated_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return ConversationListSerializer
        return ConversationDetailSerializer

    @action(detail=True, methods=['post'], url_path='messages')
    def send_message(self, request, pk=None):
        """Send a new message in this conversation."""
        conversation = self.get_object()
        serializer = MessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message = Message.objects.create(
            conversation=conversation,
            sender_type='agent',
            sender_name='Leo',
            sender_avatar='',
            content=serializer.validated_data['content'],
        )

        # Touch conversation to update ordering
        conversation.save()

        return Response(
            MessageSerializer(message).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Close a conversation."""
        conversation = self.get_object()
        conversation.status = ConversationStatus.CLOSED
        conversation.save()
        return Response(ConversationDetailSerializer(conversation).data)

    @action(detail=True, methods=['post'])
    def pin(self, request, pk=None):
        """Toggle pinned state of a conversation."""
        conversation = self.get_object()
        conversation.is_pinned = not conversation.is_pinned
        conversation.save()
        return Response(ConversationDetailSerializer(conversation).data)

    @action(detail=True, methods=['post'], url_path='ai_assist')
    def ai_assist(self, request, pk=None):
        """Generate AI-assisted context analysis and suggested reply."""
        conversation = self.get_object()
        from .ai_engine import analyze_conversation
        result = analyze_conversation(conversation)
        return Response(result)
