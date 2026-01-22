"""
API Views for the Path Library.
"""

from django.db import models
from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Issue, RootCause, Initiative, Path, Phase, Step, ActionItem, PathComment, PathStatus, ItemStatus
from .serializers import (
    IssueSerializer, IssueListSerializer,
    RootCauseSerializer, RootCauseListSerializer,
    InitiativeSerializer, InitiativeListSerializer,
    PathListSerializer, PathDetailSerializer, PathCreateSerializer, PathUpdateSerializer,
    PathStatusUpdateSerializer, ActionItemStatusSerializer,
    PhaseSerializer, PhaseListSerializer,
    StepSerializer,
    ActionItemSerializer,
    PathCommentSerializer,
)
from .filters import PathFilter, IssueFilter


class IssueViewSet(viewsets.ModelViewSet):
    """API endpoint for Issues."""
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
    """API endpoint for Root Causes."""
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
    """API endpoint for Initiatives."""
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
    Issue -> Root Cause -> Initiative -> Implementation Plan (Phases > Steps > Actions)
    """
    queryset = Path.objects.select_related(
        'issue', 'root_cause', 'initiative'
    ).prefetch_related(
        'phases__steps__action_items', 'comments'
    )
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
        """Update the status of a path."""
        path = self.get_object()
        serializer = PathStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data['status']
        old_status = path.status

        path.status = new_status

        if new_status == PathStatus.ACTIVE and old_status != PathStatus.ACTIVE:
            if not path.started_at:
                path.started_at = timezone.now()
            # Clear paused_at when reactivating
            path.paused_at = None
        elif new_status == PathStatus.ON_HOLD:
            path.paused_at = timezone.now()
        elif new_status == PathStatus.COMPLETED:
            path.completed_at = timezone.now()

        path.save()
        return Response(PathDetailSerializer(path).data)

    @action(detail=True, methods=['post'])
    def add_comment(self, request, pk=None):
        """Add a comment to a path."""
        path = self.get_object()
        serializer = PathCommentSerializer(data={**request.data, 'path': path.id})
        serializer.is_valid(raise_exception=True)
        comment = serializer.save()
        return Response(PathCommentSerializer(comment).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def library_stats(self, request):
        """Get statistics for the path library."""
        queryset = self.filter_queryset(self.get_queryset())

        stats = {
            'total_paths': queryset.count(),
            'by_status': {
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


class PhaseViewSet(viewsets.ModelViewSet):
    """API endpoint for Phases."""
    queryset = Phase.objects.select_related('path').prefetch_related('steps__action_items')
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['path', 'status']
    search_fields = ['title', 'description']
    ordering = ['order', 'created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return PhaseListSerializer
        return PhaseSerializer


class StepViewSet(viewsets.ModelViewSet):
    """API endpoint for Steps."""
    queryset = Step.objects.select_related('phase', 'phase__path').prefetch_related('action_items')
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['phase', 'status']
    search_fields = ['title', 'description']
    ordering = ['order', 'created_at']
    serializer_class = StepSerializer


class ActionItemViewSet(viewsets.ModelViewSet):
    """API endpoint for Action Items."""
    queryset = ActionItem.objects.select_related('step', 'step__phase', 'step__phase__path')
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['step', 'status', 'assignee_id']
    search_fields = ['title', 'description']
    ordering = ['order', 'created_at']
    serializer_class = ActionItemSerializer

    @action(detail=True, methods=['post'])
    def toggle_status(self, request, pk=None):
        """Toggle action item between todo and done."""
        item = self.get_object()
        if item.status == ItemStatus.DONE:
            item.status = ItemStatus.TODO
            item.completed_at = None
        else:
            item.status = ItemStatus.DONE
            item.completed_at = timezone.now()
        item.save()
        return Response(ActionItemSerializer(item).data)

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update action item status."""
        item = self.get_object()
        serializer = ActionItemStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        item.status = serializer.validated_data['status']
        if item.status == ItemStatus.DONE:
            item.completed_at = timezone.now()
        else:
            item.completed_at = None
        item.save()
        return Response(ActionItemSerializer(item).data)


class PathCommentViewSet(viewsets.ModelViewSet):
    """API endpoint for Path Comments."""
    queryset = PathComment.objects.select_related('path')
    serializer_class = PathCommentSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['path', 'author_id']
    ordering = ['-created_at']
