"""
Serializers for the Path Library API.
"""

from rest_framework import serializers
from .models import Issue, RootCause, Initiative, Path, Task, PathComment


class TaskSerializer(serializers.ModelSerializer):
    """Serializer for Task model."""
    subtasks = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'id', 'path', 'title', 'description', 'status',
            'assignee_id', 'order', 'parent_task', 'due_date',
            'completed_at', 'notes', 'subtasks', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_subtasks(self, obj):
        """Get nested subtasks."""
        if obj.subtasks.exists():
            return TaskSerializer(obj.subtasks.all(), many=True).data
        return []


class TaskCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating tasks."""

    class Meta:
        model = Task
        fields = [
            'id', 'path', 'title', 'description', 'status',
            'assignee_id', 'order', 'parent_task', 'due_date', 'notes'
        ]
        read_only_fields = ['id']


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
    task_count = serializers.SerializerMethodField()
    completed_task_count = serializers.SerializerMethodField()

    class Meta:
        model = Path
        fields = [
            'id', 'title', 'status', 'priority', 'progress_percentage',
            'issue_title', 'root_cause_title', 'initiative_title',
            'task_count', 'completed_task_count',
            'started_at', 'target_completion_date', 'created_at', 'updated_at'
        ]

    def get_task_count(self, obj):
        return obj.tasks.count()

    def get_completed_task_count(self, obj):
        return obj.tasks.filter(status='done').count()


class PathDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for a single path with all related data."""
    issue = IssueSerializer(read_only=True)
    root_cause = RootCauseSerializer(read_only=True)
    initiative = InitiativeSerializer(read_only=True)
    tasks = TaskSerializer(many=True, read_only=True)
    comments = PathCommentSerializer(many=True, read_only=True)

    class Meta:
        model = Path
        fields = [
            'id', 'title', 'goal_statement', 'status', 'priority',
            'started_at', 'target_completion_date', 'completed_at',
            'progress_percentage', 'baseline_metric', 'current_metric',
            'organization_id', 'owner_id', 'notes',
            'issue', 'root_cause', 'initiative', 'tasks', 'comments',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'progress_percentage', 'created_at', 'updated_at']


class PathCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new path."""
    tasks = TaskCreateSerializer(many=True, required=False)

    class Meta:
        model = Path
        fields = [
            'id', 'title', 'goal_statement', 'status', 'priority',
            'issue', 'root_cause', 'initiative',
            'target_completion_date', 'organization_id', 'owner_id',
            'notes', 'baseline_metric', 'tasks'
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        tasks_data = validated_data.pop('tasks', [])
        path = Path.objects.create(**validated_data)

        for task_data in tasks_data:
            Task.objects.create(path=path, **task_data)

        return path


class PathUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a path."""

    class Meta:
        model = Path
        fields = [
            'title', 'goal_statement', 'status', 'priority',
            'target_completion_date', 'notes',
            'baseline_metric', 'current_metric', 'started_at', 'completed_at'
        ]


class PathStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating path status."""
    status = serializers.ChoiceField(choices=[
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('on_hold', 'On Hold'),
        ('completed', 'Completed'),
        ('archived', 'Archived'),
    ])


class BulkTaskUpdateSerializer(serializers.Serializer):
    """Serializer for bulk updating task statuses."""
    task_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1
    )
    status = serializers.ChoiceField(choices=[
        ('todo', 'To Do'),
        ('in_progress', 'In Progress'),
        ('blocked', 'Blocked'),
        ('done', 'Done'),
    ])
