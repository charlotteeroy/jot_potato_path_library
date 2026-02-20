"""
AI Assist Engine for Customer Support Chat.

Keyword-based analysis engine that provides conversation context
(topic, sentiment, priority, key info) and generates suggested replies.
No LLM API key required.
"""

from django.utils import timezone


# --- Keyword Groups for Topic Detection ---

TOPIC_KEYWORDS = {
    'gift_card': ['gift card', 'gift cards', 'voucher', 'gift certificate', 'gift voucher'],
    'shipping': ['shipping', 'delivery', 'ship', 'deliver', 'tracking', 'track', 'courier', 'dispatch', 'shipment'],
    'payment': ['payment', 'pay', 'charge', 'charged', 'transaction', 'invoice', 'receipt'],
    'billing': ['billing', 'bill', 'subscription', 'renewal', 'renew', 'plan', 'upgrade', 'downgrade'],
    'refund': ['refund', 'money back', 'reimburse', 'reimbursement', 'credit back'],
    'return': ['return', 'exchange', 'swap', 'send back', 'return policy'],
    'technical': ['bug', 'error', 'crash', 'broken', 'not working', 'issue', 'problem', 'glitch', 'fix', 'login', 'password', 'reset'],
    'booking': ['booking', 'reservation', 'appointment', 'schedule', 'book', 'session', 'spa'],
    'general_inquiry': ['question', 'info', 'information', 'help', 'assist', 'how to', 'where', 'when'],
}

TOPIC_DISPLAY_NAMES = {
    'gift_card': 'Gift Card Request',
    'shipping': 'Shipping & Delivery',
    'payment': 'Payment Issue',
    'billing': 'Billing Inquiry',
    'refund': 'Refund Request',
    'return': 'Return / Exchange',
    'technical': 'Technical Support',
    'booking': 'Booking & Reservations',
    'general_inquiry': 'General Inquiry',
}

POSITIVE_WORDS = [
    'thank', 'thanks', 'great', 'awesome', 'amazing', 'love', 'loved',
    'happy', 'pleased', 'excellent', 'wonderful', 'perfect', 'good',
    'appreciate', 'appreciated', 'fantastic', 'enjoy', 'enjoyed',
    'helpful', 'kind', 'friendly', 'satisfied', 'glad', 'nice',
]

NEGATIVE_WORDS = [
    'angry', 'upset', 'frustrated', 'terrible', 'horrible', 'worst',
    'hate', 'disappointed', 'disappointing', 'awful', 'poor', 'bad',
    'unacceptable', 'ridiculous', 'annoyed', 'furious', 'complaint',
    'complain', 'rude', 'unhappy', 'dissatisfied', 'disgusted',
    'outraged', 'pathetic', 'useless', 'waste',
]

# --- Response Templates ---

RESPONSE_TEMPLATES = {
    'gift_card': (
        "Hi {name}! I'd be happy to help you with a gift card. "
        "We have several options available. Could you let me know "
        "what amount you'd like and whether you'd prefer a digital "
        "or physical gift card?"
    ),
    'shipping': (
        "Hi {name}! I'd be happy to help with your shipping inquiry. "
        "Let me look into the delivery details for you. Could you "
        "provide your order number so I can check the status?"
    ),
    'payment': (
        "Hi {name}! I understand you have a question about a payment. "
        "I'll look into this right away. Could you share the transaction "
        "details or order number so I can investigate?"
    ),
    'billing': (
        "Hi {name}! I'd be glad to help with your billing inquiry. "
        "Let me review your account details. Could you let me know "
        "which specific charge or plan you're asking about?"
    ),
    'refund': (
        "Hi {name}! I understand you'd like to request a refund. "
        "I'll do my best to help resolve this for you. Could you "
        "provide your order number and the reason for the refund?"
    ),
    'return': (
        "Hi {name}! I'd be happy to help with a return or exchange. "
        "Our return policy allows returns within 30 days. Could you "
        "share your order details so I can get this started?"
    ),
    'technical': (
        "Hi {name}! I'm sorry to hear you're experiencing a technical issue. "
        "Let me help troubleshoot this. Could you describe what's happening "
        "and any error messages you're seeing?"
    ),
    'booking': (
        "Hi {name}! I'd be happy to help you with your booking. "
        "We have availability for sessions and appointments. "
        "What date and time works best for you?"
    ),
    'general_inquiry': (
        "Hi {name}! Thanks for reaching out. I'd be happy to help "
        "answer your question. Could you provide a bit more detail "
        "about what you're looking for?"
    ),
}

DEFAULT_TEMPLATE = (
    "Hi {name}! Thanks for contacting us. I'd be happy to assist you. "
    "Could you provide a bit more detail about how I can help?"
)


def _detect_topic(messages_text):
    """Scan message text for keyword groups and return the best-matching topic."""
    text_lower = messages_text.lower()
    topic_scores = {}

    for topic, keywords in TOPIC_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            topic_scores[topic] = score

    if not topic_scores:
        return 'general_inquiry'

    return max(topic_scores, key=topic_scores.get)


def _analyze_sentiment(messages_text):
    """Count positive vs negative words to determine sentiment."""
    text_lower = messages_text.lower()

    positive_count = sum(1 for w in POSITIVE_WORDS if w in text_lower)
    negative_count = sum(1 for w in NEGATIVE_WORDS if w in text_lower)

    if positive_count > negative_count:
        return 'positive'
    elif negative_count > positive_count:
        return 'negative'
    return 'neutral'


def _calculate_priority(sentiment, unread_count, last_customer_message):
    """Calculate priority based on sentiment, unread count, and response time."""
    score = 0

    # Negative sentiment increases priority
    if sentiment == 'negative':
        score += 2
    elif sentiment == 'neutral':
        score += 1

    # High unread count increases priority
    if unread_count >= 5:
        score += 2
    elif unread_count >= 2:
        score += 1

    # Long wait time increases priority
    if last_customer_message:
        time_diff = timezone.now() - last_customer_message.created_at
        hours_waiting = time_diff.total_seconds() / 3600
        if hours_waiting > 24:
            score += 2
        elif hours_waiting > 4:
            score += 1

    if score >= 4:
        return 'high'
    elif score >= 2:
        return 'medium'
    return 'low'


def _extract_key_info(customer_messages):
    """Extract the last 2-3 customer messages as summary bullet points."""
    recent = customer_messages[:3]
    key_info = []
    for msg in recent:
        content = msg.content.strip()
        # Truncate long messages
        if len(content) > 120:
            content = content[:117] + '...'
        key_info.append(content)
    return key_info


def _get_customer_history(customer_name):
    """Count previous conversations with the same customer."""
    from .models import Conversation
    count = Conversation.objects.filter(customer_name=customer_name).count()
    return f"{count} previous conversation(s)"


TOPIC_SHORT_LABELS = {
    'gift_card': 'Gift Cards',
    'shipping': 'Shipping',
    'payment': 'Payments',
    'billing': 'Billing',
    'refund': 'Refunds',
    'return': 'Returns',
    'technical': 'Technical',
    'booking': 'Amenities',
    'general_inquiry': 'General',
}

SOLUTION_TEMPLATES = {
    'gift_card': (
        "Offer the customer available gift card options (digital or physical). "
        "Confirm the desired amount and delivery method, then process the order."
    ),
    'shipping': (
        "Look up the order tracking information and provide the current delivery status. "
        "If delayed, offer expedited shipping or a discount on the next order."
    ),
    'payment': (
        "Verify the transaction details in the payment system. "
        "If a charge error occurred, initiate a correction or escalate to the payments team."
    ),
    'billing': (
        "Review the customer's subscription and billing history. "
        "Clarify any charges and offer plan adjustments if needed."
    ),
    'refund': (
        "Verify the order is eligible for a refund per our policy. "
        "Process the refund and confirm the expected timeline for the credit."
    ),
    'return': (
        "Confirm the item is within the 30-day return window. "
        "Provide a return shipping label and process the exchange or refund."
    ),
    'technical': (
        "Gather error details and reproduce the issue if possible. "
        "Apply known fixes or escalate to the engineering team with a detailed report."
    ),
    'booking': (
        "Check availability for the requested service and date. "
        "Confirm the booking details and send a confirmation to the customer."
    ),
    'general_inquiry': (
        "Address the customer's question with the relevant information. "
        "If further details are needed, direct them to the appropriate resource or team."
    ),
}

ORDINALS = {1: 'first', 2: 'second', 3: 'third', 4: 'fourth', 5: 'fifth'}

TOPIC_VERB_PHRASES = {
    'gift_card': 'asking about gift cards',
    'shipping': 'asking about shipping',
    'payment': 'reporting a payment issue',
    'billing': 'inquiring about billing',
    'refund': 'requesting a refund',
    'return': 'asking about a return',
    'technical': 'reporting a technical issue',
    'booking': 'inquiring about a booking',
    'general_inquiry': 'reaching out with a question',
}

SENTIMENT_PHRASES = {
    'negative': 'and seems frustrated',
    'positive': 'and has a positive tone',
    'neutral': '',
}


def _generate_context_summary(customer_name, topic_key, sentiment, conversation_count):
    """Generate a natural language context summary sentence."""
    verb = TOPIC_VERB_PHRASES.get(topic_key, 'reaching out')
    sentiment_phrase = SENTIMENT_PHRASES.get(sentiment, '')

    if conversation_count > 1:
        ordinal = ORDINALS.get(conversation_count, f'{conversation_count}th')
        history = f"{customer_name} is a returning customer ({ordinal} conversation)"
    else:
        history = f"This is {customer_name}'s first conversation"

    parts = [f"{history}, {verb}"]
    if sentiment_phrase:
        parts[0] += f" {sentiment_phrase}"

    return parts[0] + '.'


def _generate_suggested_reply(topic, customer_name, key_info):
    """Generate a template-based suggested reply."""
    template = RESPONSE_TEMPLATES.get(topic, DEFAULT_TEMPLATE)
    reply = template.format(name=customer_name)

    # Add context-specific details if we have key info
    if key_info and topic != 'general_inquiry':
        # Check if we can personalize further based on key info content
        combined = ' '.join(key_info).lower()
        if 'friend' in combined and topic == 'gift_card':
            reply = (
                f"Hi {customer_name}! I'd be happy to help you with a gift card "
                "for your friend. We have several options available - would you "
                "prefer a digital card sent via email or a physical card?"
            )
        elif 'spa' in combined and topic == 'booking':
            reply = (
                f"Hi {customer_name}! Glad to hear you're interested in our spa services. "
                "I can help you book a session. What type of treatment are you looking for "
                "and what date works best?"
            )

    return reply


def analyze_conversation(conversation):
    """
    Analyze a conversation and return AI-assisted context and a suggested reply.

    Returns a dict with:
      - context: topic, sentiment, priority, key_info, customer_history
      - suggested_reply: a template-based reply personalized for this conversation
    """
    messages = conversation.messages.order_by('-created_at')
    customer_messages = [m for m in messages if m.sender_type == 'customer']

    # Combine all message content for analysis
    all_text = ' '.join(m.content for m in messages)

    # Run analysis
    topic_key = _detect_topic(all_text)
    sentiment = _analyze_sentiment(all_text)

    # Get last customer message for priority calculation
    last_customer_msg = customer_messages[0] if customer_messages else None

    # Unread count
    unread_count = conversation.messages.filter(
        sender_type='customer', is_read=False
    ).count()

    priority = _calculate_priority(sentiment, unread_count, last_customer_msg)
    key_info = _extract_key_info(customer_messages)
    customer_history = _get_customer_history(conversation.customer_name)

    # Count conversations for summary
    from .models import Conversation as ConvModel
    conversation_count = ConvModel.objects.filter(
        customer_name=conversation.customer_name
    ).count()

    # Generate context summary
    summary = _generate_context_summary(
        conversation.customer_name, topic_key, sentiment, conversation_count
    )

    # Generate suggested reply
    suggested_reply = _generate_suggested_reply(
        topic_key, conversation.customer_name, key_info
    )

    # Panel data for side panel
    customer_status = "Returning customer" if conversation_count > 1 else "New customer"
    ai_summary = summary
    if key_info:
        ai_summary += " " + ". ".join(key_info) + "."
    issue_type = TOPIC_SHORT_LABELS.get(topic_key, 'General')
    severity = priority.capitalize()

    # Count conversations with same topic this week
    from datetime import timedelta
    now = timezone.now()
    week_start = now - timedelta(days=7)
    prev_week_start = week_start - timedelta(days=7)

    all_convos_this_week = ConvModel.objects.filter(created_at__gte=week_start)
    all_convos_prev_week = ConvModel.objects.filter(
        created_at__gte=prev_week_start, created_at__lt=week_start
    )

    # Simple topic matching: count conversations whose messages contain topic keywords
    topic_keywords = TOPIC_KEYWORDS.get(topic_key, [])
    issue_report_count = 0
    for c in all_convos_this_week:
        c_text = ' '.join(m.content.lower() for m in c.messages.all())
        if any(kw in c_text for kw in topic_keywords):
            issue_report_count += 1

    prev_count = 0
    for c in all_convos_prev_week:
        c_text = ' '.join(m.content.lower() for m in c.messages.all())
        if any(kw in c_text for kw in topic_keywords):
            prev_count += 1

    if prev_count > 0:
        change = ((issue_report_count - prev_count) / prev_count) * 100
        issue_trend = f"+{int(change)}%" if change >= 0 else f"{int(change)}%"
    else:
        issue_trend = "+0%" if issue_report_count == 0 else "New"

    solution = SOLUTION_TEMPLATES.get(topic_key, SOLUTION_TEMPLATES['general_inquiry'])

    return {
        'context': {
            'summary': summary,
            'topic': TOPIC_DISPLAY_NAMES.get(topic_key, 'General Inquiry'),
            'sentiment': sentiment,
            'priority': priority,
            'key_info': key_info,
            'customer_history': customer_history,
        },
        'suggested_reply': suggested_reply,
        'panel': {
            'customer_status': customer_status,
            'ai_summary': ai_summary,
            'issue_type': issue_type,
            'severity': severity,
            'issue_report_count': issue_report_count,
            'issue_trend': issue_trend,
            'solution': solution,
        },
    }
