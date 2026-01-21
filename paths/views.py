"""
API Views for the Path Library.
"""

from django.db import models
from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Issue, RootCause, Initiative, Path, Task, PathComment, PathStatus
from .serializers import (
    IssueSerializer, IssueListSerializer,
    RootCauseSerializer, RootCauseListSerializer,
    InitiativeSerializer, InitiativeListSerializer,
    PathListSerializer, PathDetailSerializer, PathCreateSerializer, PathUpdateSerializer,
    PathStatusUpdateSerializer, BulkTaskUpdateSerializer,
    TaskSerializer, TaskCreateSerializer,
    PathCommentSerializer,
)
from .filters import PathFilter, IssueFilter, TaskFilter


class IssueViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Issues.

    Issues are problem statements extracted from customer feedback.
    """
    queryset = Issue.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = IssueFilter
    search_fields = ['title', 'description', 'category']
    ordering_fields = ['created_at', 'priority', 'feedback_count', 'emotional_intensity']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return IssueListSerializer
        return IssueSerializer


class RootCauseViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Root Causes.

    Root Causes explain why an issue is happening.
    """
    queryset = RootCause.objects.select_related('issue').prefetch_related('initiatives')
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['issue', 'is_ai_generated', 'cause_category']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'confidence_score']
    ordering = ['-confidence_score', '-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return RootCauseListSerializer
        return RootCauseSerializer


class InitiativeViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Initiatives.

    Initiatives are solutions to fix root causes.
    """
    queryset = Initiative.objects.select_related('root_cause', 'root_cause__issue')
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['root_cause', 'initiative_type', 'estimated_effort', 'estimated_impact', 'is_ai_generated']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'estimated_impact']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return InitiativeListSerializer
        return InitiativeSerializer


class PathViewSet(viewsets.ModelViewSet):
    """
    API endpoint for the Path Library.

    A Path represents the complete improvement journey:
    Issue -> Root Cause -> Initiative -> Tasks

    Paths can be filtered by status, priority, organization, and owner.
    """
    queryset = Path.objects.select_related(
        'issue', 'root_cause', 'initiative'
    ).prefetch_related('tasks', 'comments')
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = PathFilter
    search_fields = ['title', 'goal_statement', 'notes']
    ordering_fields = ['created_at', 'updated_at', 'priority', 'progress_percentage', 'target_completion_date']
    ordering = ['-updated_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return PathListSerializer
        if self.action == 'create':
            return PathCreateSerializer
        if self.action in ['update', 'partial_update']:
            return PathUpdateSerializer
        return PathDetailSerializer

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """
        Update the status of a path.

        POST /api/paths/{id}/update_status/
        Body: {"status": "active"}
        """
        path = self.get_object()
        serializer = PathStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data['status']
        old_status = path.status

        path.status = new_status

        # Set timestamps based on status changes
        if new_status == PathStatus.ACTIVE and old_status != PathStatus.ACTIVE:
            if not path.started_at:
                path.started_at = timezone.now()
        elif new_status == PathStatus.COMPLETED:
            path.completed_at = timezone.now()

        path.save()
        return Response(PathDetailSerializer(path).data)

    @action(detail=True, methods=['post'])
    def add_task(self, request, pk=None):
        """
        Add a task to a path.

        POST /api/paths/{id}/add_task/
        Body: {"title": "Task title", "description": "...", ...}
        """
        path = self.get_object()
        serializer = TaskCreateSerializer(data={**request.data, 'path': path.id})
        serializer.is_valid(raise_exception=True)
        task = serializer.save()
        return Response(TaskSerializer(task).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def add_comment(self, request, pk=None):
        """
        Add a comment to a path.

        POST /api/paths/{id}/add_comment/
        Body: {"author_id": "uuid", "content": "Comment text"}
        """
        path = self.get_object()
        serializer = PathCommentSerializer(data={**request.data, 'path': path.id})
        serializer.is_valid(raise_exception=True)
        comment = serializer.save()
        return Response(PathCommentSerializer(comment).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def tasks(self, request, pk=None):
        """
        Get all tasks for a path.

        GET /api/paths/{id}/tasks/
        """
        path = self.get_object()
        tasks = path.tasks.filter(parent_task__isnull=True)  # Only top-level tasks
        serializer = TaskSerializer(tasks, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def bulk_update_tasks(self, request, pk=None):
        """
        Bulk update task statuses.

        POST /api/paths/{id}/bulk_update_tasks/
        Body: {"task_ids": ["uuid1", "uuid2"], "status": "done"}
        """
        path = self.get_object()
        serializer = BulkTaskUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        task_ids = serializer.validated_data['task_ids']
        new_status = serializer.validated_data['status']

        # Only update tasks belonging to this path
        updated = path.tasks.filter(id__in=task_ids).update(
            status=new_status,
            completed_at=timezone.now() if new_status == 'done' else None
        )

        # Recalculate progress
        path.update_progress()

        return Response({
            'updated_count': updated,
            'progress_percentage': path.progress_percentage
        })

    @action(detail=False, methods=['get'])
    def library_stats(self, request):
        """
        Get statistics for the path library.

        GET /api/paths/library_stats/
        """
        queryset = self.filter_queryset(self.get_queryset())

        stats = {
            'total_paths': queryset.count(),
            'by_status': {
                'draft': queryset.filter(status=PathStatus.DRAFT).count(),
                'active': queryset.filter(status=PathStatus.ACTIVE).count(),
                'on_hold': queryset.filter(status=PathStatus.ON_HOLD).count(),
                'completed': queryset.filter(status=PathStatus.COMPLETED).count(),
                'archived': queryset.filter(status=PathStatus.ARCHIVED).count(),
            },
            'average_progress': queryset.filter(
                status=PathStatus.ACTIVE
            ).aggregate(
                avg=models.Avg('progress_percentage')
            )['avg'] or 0,
        }
        return Response(stats)


class TaskViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Tasks.

    Tasks are individual items in a path's implementation plan.
    """
    queryset = Task.objects.select_related('path', 'parent_task')
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = TaskFilter
    search_fields = ['title', 'description']
    ordering_fields = ['order', 'created_at', 'due_date', 'status']
    ordering = ['order', 'created_at']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return TaskCreateSerializer
        return TaskSerializer

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """
        Mark a task as complete.

        POST /api/tasks/{id}/complete/
        """
        task = self.get_object()
        task.status = 'done'
        task.completed_at = timezone.now()
        task.save()
        return Response(TaskSerializer(task).data)

    @action(detail=True, methods=['post'])
    def reorder(self, request, pk=None):
        """
        Reorder a task.

        POST /api/tasks/{id}/reorder/
        Body: {"order": 2}
        """
        task = self.get_object()
        new_order = request.data.get('order')
        if new_order is not None:
            task.order = int(new_order)
            task.save(update_fields=['order', 'updated_at'])
        return Response(TaskSerializer(task).data)


class PathCommentViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Path Comments.
    """
    queryset = PathComment.objects.select_related('path')
    serializer_class = PathCommentSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['path', 'author_id']
    ordering = ['-created_at']
