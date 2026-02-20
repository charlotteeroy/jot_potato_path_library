"""
Seed sample chat conversations matching the design mockup.
"""

from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from chat.models import Conversation, Message


def create_message(conversation, sender_type, sender_name, content, timestamp, is_read=True):
    """Create a message and fix the auto_now_add timestamp."""
    msg = Message.objects.create(
        conversation=conversation,
        sender_type=sender_type,
        sender_name=sender_name,
        content=content,
        is_read=is_read,
    )
    Message.objects.filter(pk=msg.pk).update(created_at=timestamp)
    return msg


class Command(BaseCommand):
    help = 'Seed sample chat conversations'

    def handle(self, *args, **options):
        Message.objects.all().delete()
        Conversation.objects.all().delete()

        now = timezone.now()

        # --- Conversation 1: Joe Johnson (Closed, last msg 5m ago) ---
        c1 = Conversation.objects.create(
            customer_name='Joe Johnson',
            customer_avatar='',
            customer_phone='+1-555-0101',
            status='closed',
        )
        for sender_type, sender_name, content, minutes_ago, is_read in [
            ('customer', 'Joe Johnson', 'Hi, I had a question about the spa session I booked last week.', 40, True),
            ('agent', 'Leo', 'Hello Joe! Of course, how can I help you with your spa session?', 38, True),
            ('customer', 'Joe Johnson', 'I was wondering if I could get a gift card for a friend. She really enjoyed the experience.', 35, True),
            ('agent', 'Leo', 'Absolutely! We have gift cards available for all our spa sessions. Feel free to reach out anytime.\nHave a wonderful day,\nLeo.', 30, True),
            ('customer', 'Joe Johnson', 'Thanks for the quick response, Leo!\nWe\'d be happy to come back for a spa session.\nThanks', 25, True),
            ('agent', 'Leo', 'Thank you for your reply!\nWe\'ve just sent you a gift card by email for a one-hour spa session.', 20, True),
            ('customer', 'Joe Johnson', 'Just received it ! Amazing.\nHave a good day !', 10, True),
            ('agent', 'Leo', 'Perfect, have a wonderful day !', 5, True),
        ]:
            create_message(c1, sender_type, sender_name, content, now - timedelta(minutes=minutes_ago), is_read)
        Conversation.objects.filter(pk=c1.pk).update(updated_at=now - timedelta(minutes=5))

        # --- Conversation 2: Michael Chen (Pending, last msg 30m ago) ---
        c2 = Conversation.objects.create(
            customer_name='Michael Chen',
            customer_avatar='',
            customer_phone='+1-555-0102',
            status='pending',
        )
        for sender_type, sender_name, content, minutes_ago, is_read in [
            ('customer', 'Michael Chen', 'Hello, I placed an order #4521 two days ago and it still hasn\'t shipped.', 35, True),
            ('agent', 'Leo', 'Hi Michael! Let me check on that order for you right away.', 33, True),
            ('customer', 'Michael Chen', 'Is there a way to expedite shipping?', 30, False),
        ]:
            create_message(c2, sender_type, sender_name, content, now - timedelta(minutes=minutes_ago), is_read)
        Conversation.objects.filter(pk=c2.pk).update(updated_at=now - timedelta(minutes=30))

        # --- Conversation 3: Emma Williams (Pending, last msg 2h ago) ---
        c3 = Conversation.objects.create(
            customer_name='Emma Williams',
            customer_avatar='',
            customer_phone='+1-555-0103',
            status='pending',
        )
        for sender_type, sender_name, content, minutes_ago, is_read in [
            ('customer', 'Emma Williams', 'Hi! I\'m having trouble with the checkout on your website. It keeps giving me an error.', 140, True),
            ('agent', 'Leo', 'Hi Emma! I\'m sorry to hear that. Could you tell me what error message you\'re seeing?', 135, True),
            ('customer', 'Emma Williams', 'It says "Payment method declined" but my card works fine everywhere else.', 130, True),
            ('agent', 'Leo', 'I see. Let me check our payment system. In the meantime, could you try using a different browser?', 125, True),
            ('customer', 'Emma Williams', 'I just tried Chrome and it worked! Thank you!', 122, True),
            ('agent', 'Leo', 'Great! I\'ll report the Safari issue to our dev team. Glad it\'s resolved for now.', 120, True),
            ('customer', 'Emma Williams', 'Perfect, that solved my issue.', 118, True),
        ]:
            create_message(c3, sender_type, sender_name, content, now - timedelta(minutes=minutes_ago), is_read)
        Conversation.objects.filter(pk=c3.pk).update(updated_at=now - timedelta(minutes=118))

        # --- Conversation 4: David Martinez (Pending, last msg 5h ago) ---
        c4 = Conversation.objects.create(
            customer_name='David Martinez',
            customer_avatar='',
            customer_phone='+1-555-0104',
            status='pending',
        )
        for sender_type, sender_name, content, minutes_ago, is_read in [
            ('customer', 'David Martinez', 'Hi, I need to update my billing information for my subscription.', 310, True),
            ('agent', 'Leo', 'Hello David! I can help you with that. For security, could you verify the email on your account?', 305, True),
            ('customer', 'David Martinez', 'Sure, it\'s david.martinez@email.com', 300, False),
        ]:
            create_message(c4, sender_type, sender_name, content, now - timedelta(minutes=minutes_ago), is_read)
        Conversation.objects.filter(pk=c4.pk).update(updated_at=now - timedelta(minutes=300))

        # --- Conversation 5: Sarah Kim (Closed, last msg ~1d ago) ---
        c5 = Conversation.objects.create(
            customer_name='Sarah Kim',
            customer_avatar='',
            customer_phone='+1-555-0105',
            status='closed',
        )
        for sender_type, sender_name, content, minutes_ago, is_read in [
            ('customer', 'Sarah Kim', 'Hi! Do you offer international shipping to South Korea?', 1500, True),
            ('agent', 'Leo', 'Hello Sarah! Yes, we do ship internationally. Delivery to South Korea usually takes 7-10 business days.', 1490, True),
            ('customer', 'Sarah Kim', 'Great, and what about customs fees?', 1480, True),
            ('agent', 'Leo', 'Customs fees vary by country. For South Korea, orders under $150 are generally duty-free. We\'ll include all relevant info in your shipping confirmation.', 1470, True),
            ('customer', 'Sarah Kim', 'Perfect, thanks for the info!', 1460, True),
        ]:
            create_message(c5, sender_type, sender_name, content, now - timedelta(minutes=minutes_ago), is_read)
        Conversation.objects.filter(pk=c5.pk).update(updated_at=now - timedelta(minutes=1460))

        self.stdout.write(self.style.SUCCESS('Successfully seeded 5 chat conversations'))
