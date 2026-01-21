"""
Django Filter classes for the Path Library API.
"""

import django_filters
from .models import Path, Issue, Task


class PathFilter(django_filters.FilterSet):
    """
    Filter for Path queryset.

    Supports filtering by:
    - status: exact match or multiple values
    - priority: exact match or multiple values
    - organization_id: exact match
    - owner_id: exact match
    - created_after: paths created after this date
    - created_before: paths created before this date
    - target_date_after: target completion date after
    - target_date_before: target completion date before
    """
    status = django_filters.MultipleChoiceFilter(
        choices=[
            ('draft', 'Draft'),
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

    created_after = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte'
    )
    created_before = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte'
    )
    target_date_after = django_filters.DateFilter(
        field_name='target_completion_date',
        lookup_expr='gte'
    )
    target_date_before = django_filters.DateFilter(
        field_name='target_completion_date',
        lookup_expr='lte'
    )

    # Progress filters
    min_progress = django_filters.NumberFilter(
        field_name='progress_percentage',
        lookup_expr='gte'
    )
    max_progress = django_filters.NumberFilter(
        field_name='progress_percentage',
        lookup_expr='lte'
    )

    # Related entity filters
    issue = django_filters.UUIDFilter()
    root_cause = django_filters.UUIDFilter()
    initiative = django_filters.UUIDFilter()

    class Meta:
        model = Path
        fields = [
            'status', 'priority', 'organization_id', 'owner_id',
            'issue', 'root_cause', 'initiative'
        ]


class IssueFilter(django_filters.FilterSet):
    """
    Filter for Issue queryset.
    """
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

    min_feedback_count = django_filters.NumberFilter(
        field_name='feedback_count',
        lookup_expr='gte'
    )
    min_emotional_intensity = django_filters.NumberFilter(
        field_name='emotional_intensity',
        lookup_expr='gte'
    )

    created_after = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte'
    )
    created_before = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte'
    )

    class Meta:
        model = Issue
        fields = ['priority', 'organization_id', 'category', 'source_channel']


class TaskFilter(django_filters.FilterSet):
    """
    Filter for Task queryset.
    """
    path = django_filters.UUIDFilter()
    status = django_filters.MultipleChoiceFilter(
        choices=[
            ('todo', 'To Do'),
            ('in_progress', 'In Progress'),
            ('blocked', 'Blocked'),
            ('done', 'Done'),
        ]
    )
    assignee_id = django_filters.UUIDFilter()

    due_after = django_filters.DateFilter(
        field_name='due_date',
        lookup_expr='gte'
    )
    due_before = django_filters.DateFilter(
        field_name='due_date',
        lookup_expr='lte'
    )

    # Filter for top-level tasks only (no parent)
    top_level_only = django_filters.BooleanFilter(
        field_name='parent_task',
        lookup_expr='isnull'
    )

    class Meta:
        model = Task
        fields = ['path', 'status', 'assignee_id']
