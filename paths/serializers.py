"""
Serializers for the Path Library API.
"""

from rest_framework import serializers
from .models import Issue, RootCause, Initiative, Path, Phase, Step, ActionItem, PathComment


class ActionItemSerializer(serializers.ModelSerializer):
    """Serializer for ActionItem model."""

    class Meta:
        model = ActionItem
        fields = [
            'id', 'step', 'title', 'description', 'status',
            'assignee_id', 'assignee_name', 'order', 'due_date', 'completed_at',
            'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class StepSerializer(serializers.ModelSerializer):
    """Serializer for Step model with nested action items."""
    action_items = ActionItemSerializer(many=True, read_only=True)
    progress = serializers.SerializerMethodField()

    class Meta:
        model = Step
        fields = [
            'id', 'phase', 'title', 'description', 'status',
            'assignee_id', 'assignee_name', 'due_date',
            'order', 'action_items', 'progress', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_progress(self, obj):
        return obj.calculate_progress()


class PhaseSerializer(serializers.ModelSerializer):
    """Serializer for Phase model with nested steps."""
    steps = StepSerializer(many=True, read_only=True)
    progress = serializers.SerializerMethodField()

    class Meta:
        model = Phase
        fields = [
            'id', 'path', 'title', 'description', 'status',
            'assignee_id', 'assignee_name', 'due_date',
            'order', 'steps', 'progress', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_progress(self, obj):
        return obj.calculate_progress()


class PhaseListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing phases."""
    step_count = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()

    class Meta:
        model = Phase
        fields = ['id', 'title', 'status', 'order', 'step_count', 'progress', 'assignee_name', 'due_date']

    def get_step_count(self, obj):
        return obj.steps.count()

    def get_progress(self, obj):
        return obj.calculate_progress()


class PathCommentSerializer(serializers.ModelSerializer):
    """Serializer for PathComment model."""

    class Meta:
        model = PathComment
        fields = ['id', 'path', 'author_id', 'content', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class InitiativeSerializer(serializers.ModelSerializer):
    """Serializer for Initiative model."""

    class Meta:
        model = Initiative
        fields = [
            'id', 'root_cause', 'title', 'description',
            'initiative_type', 'estimated_effort', 'estimated_impact',
            'is_ai_generated', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class InitiativeListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing initiatives."""

    class Meta:
        model = Initiative
        fields = ['id', 'title', 'initiative_type', 'estimated_effort', 'estimated_impact']


class RootCauseSerializer(serializers.ModelSerializer):
    """Serializer for RootCause model."""
    initiatives = InitiativeListSerializer(many=True, read_only=True)

    class Meta:
        model = RootCause
        fields = [
            'id', 'issue', 'title', 'description',
            'is_ai_generated', 'confidence_score', 'cause_category',
            'initiatives', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RootCauseListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing root causes."""

    class Meta:
        model = RootCause
        fields = ['id', 'title', 'cause_category', 'is_ai_generated', 'confidence_score']


class IssueSerializer(serializers.ModelSerializer):
    """Serializer for Issue model."""
    root_causes = RootCauseListSerializer(many=True, read_only=True)

    class Meta:
        model = Issue
        fields = [
            'id', 'title', 'description', 'source_channel',
            'feedback_count', 'category', 'priority', 'emotional_intensity',
            'organization_id', 'root_causes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class IssueListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing issues."""

    class Meta:
        model = Issue
        fields = ['id', 'title', 'category', 'priority', 'feedback_count']


class PathListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing paths in the library."""
    issue_title = serializers.CharField(source='issue.title', read_only=True)
    root_cause_title = serializers.CharField(source='root_cause.title', read_only=True)
    initiative_title = serializers.CharField(source='initiative.title', read_only=True)
    phase_count = serializers.SerializerMethodField()
    action_item_count = serializers.SerializerMethodField()
    completed_action_count = serializers.SerializerMethodField()

    class Meta:
        model = Path
        fields = [
            'id', 'title', 'status', 'priority', 'progress_percentage',
            'issue_title', 'root_cause_title', 'initiative_title',
            'phase_count', 'action_item_count', 'completed_action_count',
            'started_at', 'target_completion_date', 'completed_at', 'paused_at',
            'team_size', 'duration_days', 'project_summary',
            'created_at', 'updated_at'
        ]

    def get_phase_count(self, obj):
        return obj.phases.count()

    def get_action_item_count(self, obj):
        count = 0
        for phase in obj.phases.all():
            for step in phase.steps.all():
                count += step.action_items.count()
        return count

    def get_completed_action_count(self, obj):
        count = 0
        for phase in obj.phases.all():
            for step in phase.steps.all():
                count += step.action_items.filter(status='done').count()
        return count


class PathDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for a single path with all related data."""
    issue = IssueSerializer(read_only=True)
    root_cause = RootCauseSerializer(read_only=True)
    initiative = InitiativeSerializer(read_only=True)
    phases = PhaseSerializer(many=True, read_only=True)
    comments = PathCommentSerializer(many=True, read_only=True)

    class Meta:
        model = Path
        fields = [
            'id', 'title', 'goal_statement', 'status', 'priority',
            'started_at', 'target_completion_date', 'completed_at', 'paused_at',
            'team_size', 'duration_days', 'project_summary',
            'progress_percentage', 'baseline_metric', 'current_metric',
            'organization_id', 'owner_id', 'notes',
            # On Hold fields
            'on_hold_reason', 'what_was_started', 'on_hold_issues_faced',
            # Completed fields
            'what_was_solved', 'completed_issues_faced', 'key_learnings',
            'issue', 'root_cause', 'initiative', 'phases', 'comments',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'progress_percentage', 'created_at', 'updated_at']


class PathCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new path."""

    class Meta:
        model = Path
        fields = [
            'id', 'title', 'goal_statement', 'status', 'priority',
            'issue', 'root_cause', 'initiative',
            'target_completion_date', 'organization_id', 'owner_id',
            'notes', 'baseline_metric', 'team_size', 'project_summary'
        ]
        read_only_fields = ['id']


class PathUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a path."""

    class Meta:
        model = Path
        fields = [
            'title', 'goal_statement', 'status', 'priority',
            'target_completion_date', 'notes',
            'baseline_metric', 'current_metric', 'started_at', 'completed_at', 'paused_at',
            'team_size', 'duration_days', 'project_summary',
            # On Hold fields
            'on_hold_reason', 'what_was_started', 'on_hold_issues_faced',
            # Completed fields
            'what_was_solved', 'completed_issues_faced', 'key_learnings'
        ]


class PathStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating path status."""
    status = serializers.ChoiceField(choices=[
        ('active', 'Active'),
        ('on_hold', 'On Hold'),
        ('completed', 'Completed'),
        ('archived', 'Archived'),
    ])


class ActionItemStatusSerializer(serializers.Serializer):
    """Serializer for updating action item status."""
    status = serializers.ChoiceField(choices=[
        ('todo', 'To Do'),
        ('in_progress', 'In Progress'),
        ('blocked', 'Blocked'),
        ('done', 'Done'),
    ])
