"""
Django Filter classes for the Path Library API.
"""

import django_filters
from .models import Path, Issue


class PathFilter(django_filters.FilterSet):
    """Filter for Path queryset."""
    status = django_filters.MultipleChoiceFilter(
        choices=[
            ('active', 'Active'),
            ('on_hold', 'On Hold'),
            ('completed', 'Completed'),
            ('archived', 'Archived'),
        ]
    )
    priority = django_filters.MultipleChoiceFilter(
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('critical', 'Critical'),
        ]
    )
    organization_id = django_filters.UUIDFilter()
    owner_id = django_filters.UUIDFilter()

    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    target_date_after = django_filters.DateFilter(field_name='target_completion_date', lookup_expr='gte')
    target_date_before = django_filters.DateFilter(field_name='target_completion_date', lookup_expr='lte')

    min_progress = django_filters.NumberFilter(field_name='progress_percentage', lookup_expr='gte')
    max_progress = django_filters.NumberFilter(field_name='progress_percentage', lookup_expr='lte')

    issue = django_filters.UUIDFilter()
    root_cause = django_filters.UUIDFilter()
    initiative = django_filters.UUIDFilter()

    class Meta:
        model = Path
        fields = ['status', 'priority', 'organization_id', 'owner_id', 'issue', 'root_cause', 'initiative']


class IssueFilter(django_filters.FilterSet):
    """Filter for Issue queryset."""
    priority = django_filters.MultipleChoiceFilter(
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('critical', 'Critical'),
        ]
    )
    organization_id = django_filters.UUIDFilter()
    category = django_filters.CharFilter(lookup_expr='icontains')
    source_channel = django_filters.CharFilter(lookup_expr='icontains')

    min_feedback_count = django_filters.NumberFilter(field_name='feedback_count', lookup_expr='gte')
    min_emotional_intensity = django_filters.NumberFilter(field_name='emotional_intensity', lookup_expr='gte')

    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = Issue
        fields = ['priority', 'organization_id', 'category', 'source_channel']
