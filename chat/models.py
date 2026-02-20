"""
Customer Support Chat Models.

Conversations represent WhatsApp chat threads with customers.
Messages are individual messages within a conversation.
"""

import uuid
from django.db import models


class ConversationStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    CLOSED = 'closed', 'Closed'


class SenderType(models.TextChoices):
    CUSTOMER = 'customer', 'Customer'
    AGENT = 'agent', 'Agent'


class BaseModel(models.Model):
    """Abstract base model with common fields."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Conversation(BaseModel):
    """A WhatsApp conversation thread with a customer."""
    customer_name = models.CharField(max_length=255)
    customer_avatar = models.URLField(blank=True, default='')
    customer_phone = models.CharField(max_length=20, blank=True, default='')
    is_pinned = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=ConversationStatus.choices,
        default=ConversationStatus.PENDING,
    )

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"Conversation with {self.customer_name}"

    @property
    def last_message(self):
        return self.messages.order_by('-created_at').first()

    @property
    def unread_count(self):
        return self.messages.filter(sender_type=SenderType.CUSTOMER, is_read=False).count()


class Message(BaseModel):
    """A single message in a conversation."""
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    sender_type = models.CharField(
        max_length=20,
        choices=SenderType.choices,
    )
    sender_name = models.CharField(max_length=255)
    sender_avatar = models.URLField(blank=True, default='')
    content = models.TextField()
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender_name}: {self.content[:50]}"
