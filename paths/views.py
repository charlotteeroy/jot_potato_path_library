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

    @action(detail=True, methods=['post'])
    def ai_query(self, request, pk=None):
        """
        AI-powered query endpoint for path intelligence.
        Analyzes the path data and provides relevant insights.
        """
        path = self.get_object()
        query = request.data.get('query', '').lower()

        # Gather path data for context
        total_actions = 0
        completed_actions = 0
        blocked_actions = []
        in_progress_actions = []
        upcoming_due = []
        all_assignees = set()

        for phase in path.phases.all():
            if phase.assignee_name:
                all_assignees.add(phase.assignee_name)
            for step in phase.steps.all():
                if step.assignee_name:
                    all_assignees.add(step.assignee_name)
                for item in step.action_items.all():
                    total_actions += 1
                    if item.assignee_name:
                        all_assignees.add(item.assignee_name)
                    if item.status == ItemStatus.DONE:
                        completed_actions += 1
                    elif item.status == ItemStatus.BLOCKED:
                        blocked_actions.append({
                            'title': item.title,
                            'step': step.title,
                            'phase': phase.title,
                            'assignee': item.assignee_name
                        })
                    elif item.status == ItemStatus.IN_PROGRESS:
                        in_progress_actions.append({
                            'title': item.title,
                            'step': step.title,
                            'phase': phase.title,
                            'assignee': item.assignee_name
                        })
                    if item.due_date and item.status != ItemStatus.DONE:
                        upcoming_due.append({
                            'title': item.title,
                            'due_date': item.due_date,
                            'assignee': item.assignee_name
                        })

        # Sort upcoming by due date
        upcoming_due.sort(key=lambda x: x['due_date'])

        # Generate contextual response based on query
        response = self._generate_ai_response(
            query, path, total_actions, completed_actions,
            blocked_actions, in_progress_actions, upcoming_due, all_assignees
        )

        return Response({'response': response})

    def _generate_ai_response(self, query, path, total_actions, completed_actions,
                              blocked_actions, in_progress_actions, upcoming_due, all_assignees):
        """Generate an intelligent response based on the query and path data."""

        # Status and progress queries
        if any(word in query for word in ['status', 'progress', 'overview', 'how']):
            status_map = {'active': 'Active', 'on_hold': 'On Hold', 'completed': 'Completed'}
            status_text = status_map.get(path.status, path.status)
            progress = path.progress_percentage

            response = f"📊 **Path Status Overview**\n\n"
            response += f"**{path.title}** is currently **{status_text}** with **{progress}%** completion.\n\n"
            response += f"• Total actions: {total_actions}\n"
            response += f"• Completed: {completed_actions}\n"
            response += f"• Remaining: {total_actions - completed_actions}\n"

            if blocked_actions:
                response += f"• ⚠️ Blocked: {len(blocked_actions)}\n"
            if in_progress_actions:
                response += f"• 🔄 In Progress: {len(in_progress_actions)}\n"

            if path.target_completion_date:
                response += f"\n📅 Target completion: {path.target_completion_date.strftime('%B %d, %Y')}"

            return response

        # Blockers and issues queries
        if any(word in query for word in ['block', 'issue', 'problem', 'stuck']):
            if not blocked_actions:
                return "✅ Great news! There are currently no blocked tasks in this path. All items are either completed, in progress, or pending."

            response = f"⚠️ **Blocked Items ({len(blocked_actions)})**\n\n"
            for i, item in enumerate(blocked_actions[:5], 1):
                response += f"{i}. **{item['title']}**\n"
                response += f"   └─ {item['phase']} → {item['step']}\n"
                if item['assignee']:
                    response += f"   └─ Assigned to: {item['assignee']}\n"
                response += "\n"

            if len(blocked_actions) > 5:
                response += f"... and {len(blocked_actions) - 5} more blocked items."

            return response

        # Due dates and deadlines
        if any(word in query for word in ['due', 'deadline', 'upcoming', 'soon']):
            if not upcoming_due:
                return "📅 There are no pending tasks with due dates in this path."

            from datetime import date
            today = date.today()
            response = "📅 **Upcoming Due Dates**\n\n"

            for i, item in enumerate(upcoming_due[:7], 1):
                days_until = (item['due_date'] - today).days
                urgency = "🔴" if days_until < 0 else "🟠" if days_until <= 3 else "🟡" if days_until <= 7 else "🟢"

                if days_until < 0:
                    time_text = f"**OVERDUE** by {abs(days_until)} days"
                elif days_until == 0:
                    time_text = "**DUE TODAY**"
                elif days_until == 1:
                    time_text = "Due tomorrow"
                else:
                    time_text = f"Due in {days_until} days"

                response += f"{urgency} **{item['title']}**\n"
                response += f"   └─ {time_text} ({item['due_date'].strftime('%b %d')})\n"
                if item['assignee']:
                    response += f"   └─ Assignee: {item['assignee']}\n"
                response += "\n"

            return response

        # Accomplishments and completed work
        if any(word in query for word in ['accomplish', 'done', 'complete', 'finish', 'solved']):
            if completed_actions == 0:
                return "📋 No tasks have been completed yet. The team is just getting started on this path!"

            response = f"✅ **Accomplishments**\n\n"
            response += f"**{completed_actions}** out of **{total_actions}** action items have been completed ({path.progress_percentage}%).\n\n"

            if path.what_was_solved:
                response += "**Key achievements:**\n"
                for item in path.what_was_solved:
                    response += f"• {item}\n"

            if path.key_learnings:
                response += "\n**Key learnings:**\n"
                for item in path.key_learnings:
                    response += f"• {item}\n"

            return response

        # Team and assignees
        if any(word in query for word in ['team', 'who', 'assignee', 'member', 'person']):
            if not all_assignees:
                return "👥 No team members have been assigned to tasks in this path yet."

            response = f"👥 **Team Members** ({len(all_assignees)})\n\n"
            for name in sorted(all_assignees):
                response += f"• {name}\n"

            response += f"\n📊 Team size: {path.team_size or 1} member(s)"
            return response

        # Phase information
        if any(word in query for word in ['phase', 'stage', 'step']):
            phases = list(path.phases.all().order_by('order'))
            if not phases:
                return "📋 No phases have been defined for this path yet."

            response = "📋 **Implementation Phases**\n\n"
            for phase in phases:
                progress = phase.calculate_progress()
                status_emoji = "✅" if phase.status == 'done' else "🔄" if phase.status == 'in_progress' else "⏳"
                response += f"{status_emoji} **{phase.title}** - {progress}%\n"
                response += f"   └─ {phase.steps.count()} steps\n"
                if phase.assignee_name:
                    response += f"   └─ Lead: {phase.assignee_name}\n"
                response += "\n"

            return response

        # Default response with general info
        response = f"🥔 **About this Path**\n\n"
        response += f"**{path.title}**\n\n"

        if path.goal_statement:
            response += f"**Goal:** {path.goal_statement}\n\n"
        if path.project_summary:
            response += f"**Summary:** {path.project_summary}\n\n"

        response += f"**Current Status:** {path.status.replace('_', ' ').title()}\n"
        response += f"**Progress:** {path.progress_percentage}% ({completed_actions}/{total_actions} tasks)\n"

        if path.issue:
            response += f"\n**Original Issue:** {path.issue.title}"
        if path.root_cause:
            response += f"\n**Root Cause:** {path.root_cause.title}"
        if path.initiative:
            response += f"\n**Initiative:** {path.initiative.title}"

        response += "\n\n💡 *Try asking about: status, blockers, due dates, team, phases, or accomplishments*"

        return response


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
