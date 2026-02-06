"""
API Views for the Path Library.
"""

from datetime import date, timedelta
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

        # Build comprehensive path context
        context = self._build_path_context(path)

        # Generate contextual response based on query
        response = self._generate_ai_response(query, path, context)

        return Response({'response': response})

    def _build_path_context(self, path):
        """Build a comprehensive context object with all path data."""
        today = date.today()

        context = {
            # Basic stats
            'total_actions': 0,
            'completed_actions': 0,
            'blocked_actions': [],
            'in_progress_actions': [],
            'todo_actions': [],
            'overdue_actions': [],
            'upcoming_due': [],
            'all_assignees': set(),

            # Phase details
            'phases': [],
            'completed_phases': 0,
            'in_progress_phases': 0,

            # Timeline
            'earliest_due': None,
            'latest_due': None,
            'days_active': 0,

            # Team workload
            'assignee_workload': {},

            # Categories and priorities
            'by_priority': {'critical': 0, 'high': 0, 'medium': 0, 'low': 0},
            'by_category': {},
        }

        # Calculate days active
        if path.started_at:
            context['days_active'] = (today - path.started_at.date()).days

        # Process all phases, steps, and action items
        for phase in path.phases.all().order_by('order'):
            phase_data = {
                'title': phase.title,
                'description': phase.description,
                'status': phase.status,
                'progress': phase.calculate_progress(),
                'assignee': phase.assignee_name,
                'due_date': phase.due_date,
                'priority': phase.priority,
                'category': phase.category,
                'workload_days': phase.workload_days,
                'steps': [],
                'total_actions': 0,
                'completed_actions': 0,
            }

            if phase.status == ItemStatus.DONE:
                context['completed_phases'] += 1
            elif phase.status == ItemStatus.IN_PROGRESS:
                context['in_progress_phases'] += 1

            if phase.assignee_name:
                context['all_assignees'].add(phase.assignee_name)
                if phase.assignee_name not in context['assignee_workload']:
                    context['assignee_workload'][phase.assignee_name] = {'total': 0, 'completed': 0, 'in_progress': 0, 'blocked': 0}

            for step in phase.steps.all().order_by('order'):
                step_data = {
                    'title': step.title,
                    'description': step.description,
                    'status': step.status,
                    'progress': step.calculate_progress(),
                    'assignee': step.assignee_name,
                    'due_date': step.due_date,
                    'priority': step.priority,
                    'category': step.category,
                    'action_items': [],
                }

                if step.assignee_name:
                    context['all_assignees'].add(step.assignee_name)
                    if step.assignee_name not in context['assignee_workload']:
                        context['assignee_workload'][step.assignee_name] = {'total': 0, 'completed': 0, 'in_progress': 0, 'blocked': 0}

                if step.category:
                    context['by_category'][step.category] = context['by_category'].get(step.category, 0) + 1

                for item in step.action_items.all().order_by('order'):
                    context['total_actions'] += 1
                    phase_data['total_actions'] += 1

                    item_data = {
                        'title': item.title,
                        'description': item.description,
                        'status': item.status,
                        'assignee': item.assignee_name,
                        'due_date': item.due_date,
                        'completed_at': item.completed_at,
                        'notes': item.notes,
                        'phase': phase.title,
                        'step': step.title,
                    }

                    if item.assignee_name:
                        context['all_assignees'].add(item.assignee_name)
                        if item.assignee_name not in context['assignee_workload']:
                            context['assignee_workload'][item.assignee_name] = {'total': 0, 'completed': 0, 'in_progress': 0, 'blocked': 0}
                        context['assignee_workload'][item.assignee_name]['total'] += 1

                    if item.status == ItemStatus.DONE:
                        context['completed_actions'] += 1
                        phase_data['completed_actions'] += 1
                        if item.assignee_name:
                            context['assignee_workload'][item.assignee_name]['completed'] += 1
                    elif item.status == ItemStatus.BLOCKED:
                        context['blocked_actions'].append(item_data)
                        if item.assignee_name:
                            context['assignee_workload'][item.assignee_name]['blocked'] += 1
                    elif item.status == ItemStatus.IN_PROGRESS:
                        context['in_progress_actions'].append(item_data)
                        if item.assignee_name:
                            context['assignee_workload'][item.assignee_name]['in_progress'] += 1
                    else:
                        context['todo_actions'].append(item_data)

                    # Track due dates
                    if item.due_date and item.status != ItemStatus.DONE:
                        if item.due_date < today:
                            context['overdue_actions'].append(item_data)
                        context['upcoming_due'].append(item_data)

                        if context['earliest_due'] is None or item.due_date < context['earliest_due']:
                            context['earliest_due'] = item.due_date
                        if context['latest_due'] is None or item.due_date > context['latest_due']:
                            context['latest_due'] = item.due_date

                    step_data['action_items'].append(item_data)

                phase_data['steps'].append(step_data)

            context['phases'].append(phase_data)

        # Sort lists
        context['upcoming_due'].sort(key=lambda x: x['due_date'] if x['due_date'] else today + timedelta(days=9999))
        context['overdue_actions'].sort(key=lambda x: x['due_date'] if x['due_date'] else today)

        return context

    def _is_completed_or_archived(self, path):
        """Check if path is in a finished state."""
        return path.status in (PathStatus.COMPLETED, PathStatus.ARCHIVED)

    def _generate_ai_response(self, query, path, ctx):
        """Generate an intelligent response based on the query and comprehensive path context."""
        today = date.today()

        # Split query into individual words for word-level matching
        words = query.split()

        def has_word(targets):
            """Check if any target word appears as a standalone word in the query."""
            return any(w in words for w in targets)

        def has_phrase(targets):
            """Check if any target phrase appears anywhere in the query string."""
            return any(phrase in query for phrase in targets)

        # --- PHASE 1: Check multi-word phrases first (most specific) ---

        if has_phrase(['how can we improve', 'how to improve', 'what to improve', 'how do we improve',
                       'can we improve', 'suggestions for', 'recommendations for', 'advice on']):
            return self._response_improvements(path, ctx)

        if has_phrase(['what went well', 'what was achieved', 'what did we accomplish',
                       'what was solved', 'what we solved', 'what was done']):
            return self._response_accomplishments(path, ctx)

        if has_phrase(['root cause', 'where does it come from', 'why is this happening',
                       'what caused', 'original issue', 'source of']):
            return self._response_issue_chain(path, ctx)

        if has_phrase(['on hold', 'why paused', 'why stopped', 'put on hold']):
            return self._response_on_hold(path, ctx)

        if has_phrase(['how is it going', 'how are we doing', 'where are we',
                       'what is the status', 'current status', 'project status']):
            return self._response_status_overview(path, ctx)

        if has_phrase(['success factor', 'key factor', 'what made it work', 'why it worked']):
            return self._response_success_factors(path, ctx)

        if has_phrase(['tell me about', 'tell me everything', 'full summary', 'complete summary']):
            return self._response_full_summary(path, ctx)

        # --- PHASE 2: Check specific intent words (before generic ones) ---

        # Improvements and recommendations
        if has_word(['improve', 'better', 'recommend', 'suggest', 'advice', 'optimize', 'enhance']):
            return self._response_improvements(path, ctx)

        # Blockers and risks
        if has_word(['blocker', 'blocked', 'blockers', 'stuck', 'risk', 'risks']):
            return self._response_blockers(path, ctx)

        # Learning and insights
        if has_word(['learn', 'learning', 'learnings', 'insight', 'insights', 'takeaway', 'lesson', 'lessons']):
            return self._response_learnings(path, ctx)

        # Due dates and deadlines
        if has_word(['due', 'deadline', 'deadlines', 'upcoming', 'overdue', 'late']):
            return self._response_deadlines(path, ctx, today)

        # Accomplishments and completed work
        if has_word(['accomplish', 'accomplished', 'accomplishments', 'solved', 'achieved', 'achievements']):
            return self._response_accomplishments(path, ctx)

        # Team and assignees
        if has_word(['team', 'assignee', 'member', 'members', 'people', 'workload']):
            return self._response_team(path, ctx)

        # Phase information
        if has_word(['phase', 'phases', 'stage', 'stages', 'implementation']):
            return self._response_phases(path, ctx)

        # Step information
        if has_word(['step', 'steps', 'task', 'tasks', 'action', 'actions', 'activity']):
            return self._response_steps(path, ctx)

        # Timeline and duration
        if has_word(['timeline', 'duration', 'schedule']):
            return self._response_timeline(path, ctx, today)

        # Goal and purpose
        if has_word(['goal', 'purpose', 'objective', 'aim', 'target']):
            return self._response_goal(path, ctx)

        # Success factors
        if has_word(['success', 'factor', 'factors']):
            return self._response_success_factors(path, ctx)

        # On hold / paused information
        if has_word(['hold', 'pause', 'paused', 'delay', 'delayed']):
            return self._response_on_hold(path, ctx)

        # Summary
        if has_word(['summary', 'everything', 'full', 'detail', 'details']):
            return self._response_full_summary(path, ctx)

        # Issue chain
        if has_word(['issue', 'root', 'cause', 'initiative', 'origin', 'source', 'feedback']):
            return self._response_issue_chain(path, ctx)

        # --- PHASE 3: Generic / fallback words ---

        if has_word(['status', 'progress', 'overview', 'doing', 'going']):
            return self._response_status_overview(path, ctx)

        if has_word(['challenge', 'challenges', 'problem', 'problems']):
            return self._response_blockers(path, ctx)

        if has_word(['done', 'complete', 'completed', 'finish', 'finished']):
            return self._response_accomplishments(path, ctx)

        if has_word(['who']):
            return self._response_team(path, ctx)

        if has_word(['plan']):
            return self._response_phases(path, ctx)

        if has_word(['when', 'start', 'end', 'long', 'time']):
            return self._response_timeline(path, ctx, today)

        if has_word(['why']):
            return self._response_goal(path, ctx)

        if has_word(['how']):
            return self._response_status_overview(path, ctx)

        if has_word(['help']):
            return self._response_improvements(path, ctx)

        # Default response with comprehensive info
        return self._response_default(path, ctx)

    def _response_status_overview(self, path, ctx):
        """Generate status overview response."""
        status_map = {'active': 'Active', 'on_hold': 'On Hold', 'completed': 'Completed', 'archived': 'Archived'}
        status_text = status_map.get(path.status, path.status)

        response = f"📊 **Path Status Overview**\n\n"
        response += f"**{path.title}**\n"
        response += f"Status: **{status_text}** | Progress: **{path.progress_percentage}%**\n\n"

        response += f"**Action Items:**\n"
        response += f"• ✅ Completed: {ctx['completed_actions']}/{ctx['total_actions']}\n"
        response += f"• 🔄 In Progress: {len(ctx['in_progress_actions'])}\n"
        response += f"• ⏳ To Do: {len(ctx['todo_actions'])}\n"

        if ctx['blocked_actions']:
            response += f"• ⚠️ Blocked: {len(ctx['blocked_actions'])}\n"
        if ctx['overdue_actions']:
            response += f"• 🔴 Overdue: {len(ctx['overdue_actions'])}\n"

        response += f"\n**Phases:** {ctx['completed_phases']}/{len(ctx['phases'])} completed"

        if ctx['in_progress_phases'] > 0:
            response += f", {ctx['in_progress_phases']} in progress"

        if self._is_completed_or_archived(path):
            if path.completed_at:
                response += f"\n\n🏁 **Completed on** {path.completed_at.strftime('%B %d, %Y')}"
            if path.what_was_solved:
                response += f"\n✅ {len(path.what_was_solved)} outcome(s) documented"
        elif path.target_completion_date:
            days_left = (path.target_completion_date - date.today()).days
            if days_left > 0:
                response += f"\n\n📅 **{days_left} days** until target completion ({path.target_completion_date.strftime('%B %d, %Y')})"
            elif days_left == 0:
                response += f"\n\n📅 Target completion is **TODAY**!"
            else:
                response += f"\n\n🔴 Target completion was **{abs(days_left)} days ago**"

        if ctx['all_assignees']:
            response += f"\n👥 **{len(ctx['all_assignees'])}** team members involved"

        return response

    def _response_blockers(self, path, ctx):
        """Generate blockers and risks response."""
        response = "⚠️ **Blockers & Risks**\n\n"

        if not ctx['blocked_actions'] and not ctx['overdue_actions']:
            response += "✅ **No current blockers or overdue items!**\n\n"

            if self._is_completed_or_archived(path):
                response += "This path has been completed with no unresolved blockers."
            elif path.status == PathStatus.ON_HOLD:
                response += "No blockers were recorded before this path was paused."
            else:
                response += "All tasks are on track."

            # Add potential risks (only relevant for active paths)
            if not self._is_completed_or_archived(path) and len(ctx['in_progress_actions']) > 5:
                response += f"\n\n⚡ **Potential risk:** {len(ctx['in_progress_actions'])} items are in progress simultaneously. Consider focusing on fewer items."

            return response

        if ctx['blocked_actions']:
            response += f"**🚫 Blocked Tasks ({len(ctx['blocked_actions'])})**\n\n"
            for i, item in enumerate(ctx['blocked_actions'][:5], 1):
                response += f"{i}. **{item['title']}**\n"
                response += f"   📍 {item['phase']} → {item['step']}\n"
                if item['assignee']:
                    response += f"   👤 {item['assignee']}\n"
            if len(ctx['blocked_actions']) > 5:
                response += f"\n... and {len(ctx['blocked_actions']) - 5} more\n"

        if ctx['overdue_actions']:
            response += f"\n**🔴 Overdue Tasks ({len(ctx['overdue_actions'])})**\n\n"
            for i, item in enumerate(ctx['overdue_actions'][:5], 1):
                days_overdue = (date.today() - item['due_date']).days
                response += f"{i}. **{item['title']}** - {days_overdue} days overdue\n"
                if item['assignee']:
                    response += f"   👤 {item['assignee']}\n"

        return response

    def _response_deadlines(self, path, ctx, today):
        """Generate deadlines response."""
        if self._is_completed_or_archived(path):
            response = "📅 **Timeline Summary**\n\n"
            response += "This path has been completed — there are no pending deadlines.\n\n"
            if path.started_at:
                response += f"**Started:** {path.started_at.strftime('%B %d, %Y')}\n"
            if path.completed_at:
                response += f"**Completed:** {path.completed_at.strftime('%B %d, %Y')}\n"
            if path.started_at and path.completed_at:
                duration = (path.completed_at.date() - path.started_at.date()).days
                response += f"**Duration:** {duration} days\n"
            if path.target_completion_date:
                if path.completed_at and path.completed_at.date() <= path.target_completion_date:
                    response += "\n✅ Completed on or before the target date."
                elif path.completed_at and path.completed_at.date() > path.target_completion_date:
                    days_late = (path.completed_at.date() - path.target_completion_date).days
                    response += f"\n⚠️ Completed {days_late} day(s) after the target date."
            return response

        if not ctx['upcoming_due']:
            return "📅 **No pending tasks with due dates.**\n\nAll tasks either have no due date set or are already completed."

        response = "📅 **Upcoming Deadlines**\n\n"

        # Group by urgency
        overdue = [x for x in ctx['upcoming_due'] if x['due_date'] and x['due_date'] < today]
        this_week = [x for x in ctx['upcoming_due'] if x['due_date'] and today <= x['due_date'] <= today + timedelta(days=7)]
        later = [x for x in ctx['upcoming_due'] if x['due_date'] and x['due_date'] > today + timedelta(days=7)]

        if overdue:
            response += f"**🔴 OVERDUE ({len(overdue)})**\n"
            for item in overdue[:3]:
                days = (today - item['due_date']).days
                response += f"• {item['title']} ({days}d late)"
                if item['assignee']:
                    response += f" - {item['assignee']}"
                response += "\n"
            response += "\n"

        if this_week:
            response += f"**🟠 This Week ({len(this_week)})**\n"
            for item in this_week[:5]:
                days = (item['due_date'] - today).days
                day_text = "TODAY" if days == 0 else f"in {days}d"
                response += f"• {item['title']} ({day_text})"
                if item['assignee']:
                    response += f" - {item['assignee']}"
                response += "\n"
            response += "\n"

        if later:
            response += f"**🟢 Later ({len(later)})**\n"
            for item in later[:3]:
                response += f"• {item['title']} ({item['due_date'].strftime('%b %d')})\n"

        return response

    def _response_accomplishments(self, path, ctx):
        """Generate accomplishments response."""
        response = "✅ **Accomplishments & Progress**\n\n"

        if ctx['completed_actions'] == 0:
            response += "No tasks have been completed yet.\n"
            if ctx['in_progress_actions']:
                response += f"\n🔄 **{len(ctx['in_progress_actions'])} tasks** are currently in progress."
            return response

        response += f"**{ctx['completed_actions']}** of **{ctx['total_actions']}** action items completed (**{path.progress_percentage}%**)\n\n"

        # Show completed phases
        completed_phases = [p for p in ctx['phases'] if p['status'] == 'done']
        if completed_phases:
            response += "**Completed Phases:**\n"
            for phase in completed_phases:
                response += f"✅ {phase['title']}\n"
            response += "\n"

        # Show what was solved (if available)
        if path.what_was_solved:
            response += "**What Was Solved:**\n"
            for item in path.what_was_solved:
                response += f"• {item}\n"
            response += "\n"

        # Show key learnings (if available)
        if path.key_learnings:
            response += "**Key Learnings:**\n"
            for item in path.key_learnings:
                response += f"• {item}\n"

        return response

    def _response_team(self, path, ctx):
        """Generate team information response."""
        if not ctx['all_assignees']:
            return "👥 **Team**\n\nNo team members have been assigned to this path yet."

        response = f"👥 **Team ({len(ctx['all_assignees'])} members)**\n\n"

        for name in sorted(ctx['all_assignees']):
            workload = ctx['assignee_workload'].get(name, {})
            total = workload.get('total', 0)
            completed = workload.get('completed', 0)
            in_progress = workload.get('in_progress', 0)
            blocked = workload.get('blocked', 0)

            response += f"**{name}**\n"
            if total > 0:
                response += f"   • Tasks: {completed}/{total} done"
                if in_progress:
                    response += f", {in_progress} in progress"
                if blocked:
                    response += f", ⚠️ {blocked} blocked"
                response += "\n"
            response += "\n"

        if path.team_size:
            response += f"📊 Official team size: {path.team_size} member(s)"

        return response

    def _response_phases(self, path, ctx):
        """Generate phases information response."""
        if not ctx['phases']:
            return "📋 **Implementation Plan**\n\nNo phases have been defined yet."

        response = "📋 **Implementation Phases**\n\n"

        for i, phase in enumerate(ctx['phases'], 1):
            status_emoji = "✅" if phase['status'] == 'done' else "🔄" if phase['status'] == 'in_progress' else "⏳"
            response += f"{status_emoji} **Phase {i}: {phase['title']}** ({phase['progress']}%)\n"

            if phase['description']:
                response += f"   {phase['description'][:100]}{'...' if len(phase['description']) > 100 else ''}\n"

            response += f"   • {len(phase['steps'])} steps, {phase['completed_actions']}/{phase['total_actions']} tasks done\n"

            if phase['assignee']:
                response += f"   • Lead: {phase['assignee']}\n"
            if phase['due_date']:
                response += f"   • Due: {phase['due_date'].strftime('%b %d, %Y')}\n"
            if phase['priority'] and phase['priority'] != 'medium':
                response += f"   • Priority: {phase['priority'].upper()}\n"

            response += "\n"

        return response

    def _response_steps(self, path, ctx):
        """Generate steps/tasks information response."""
        if self._is_completed_or_archived(path):
            response = "📝 **Steps & Tasks (Final Summary)**\n\n"
            response += f"**Results:**\n"
            response += f"• Total action items: {ctx['total_actions']}\n"
            response += f"• Completed: {ctx['completed_actions']}\n"
            if ctx['total_actions'] > ctx['completed_actions']:
                remaining = ctx['total_actions'] - ctx['completed_actions']
                response += f"• Not completed: {remaining}\n"
            response += f"\n**Phases:** {ctx['completed_phases']}/{len(ctx['phases'])} completed\n"
            return response

        response = "📝 **Steps & Tasks**\n\n"

        response += f"**Summary:**\n"
        response += f"• Total action items: {ctx['total_actions']}\n"
        response += f"• Completed: {ctx['completed_actions']}\n"
        response += f"• In Progress: {len(ctx['in_progress_actions'])}\n"
        response += f"• To Do: {len(ctx['todo_actions'])}\n"
        response += f"• Blocked: {len(ctx['blocked_actions'])}\n\n"

        # Show in-progress items
        if ctx['in_progress_actions']:
            response += "**🔄 Currently In Progress:**\n"
            for item in ctx['in_progress_actions'][:5]:
                response += f"• {item['title']}"
                if item['assignee']:
                    response += f" ({item['assignee']})"
                response += "\n"
            if len(ctx['in_progress_actions']) > 5:
                response += f"... and {len(ctx['in_progress_actions']) - 5} more\n"

        return response

    def _response_timeline(self, path, ctx, today):
        """Generate timeline information response."""
        response = "📅 **Timeline**\n\n"

        if path.started_at:
            response += f"**Started:** {path.started_at.strftime('%B %d, %Y')} ({ctx['days_active']} days ago)\n"

        if path.target_completion_date:
            days_to_target = (path.target_completion_date - today).days
            response += f"**Target Completion:** {path.target_completion_date.strftime('%B %d, %Y')}"
            if days_to_target > 0:
                response += f" ({days_to_target} days remaining)\n"
            elif days_to_target == 0:
                response += " (TODAY)\n"
            else:
                response += f" ({abs(days_to_target)} days overdue)\n"

        if path.completed_at:
            response += f"**Completed:** {path.completed_at.strftime('%B %d, %Y')}\n"

        if path.paused_at:
            response += f"**Paused:** {path.paused_at.strftime('%B %d, %Y')}\n"

        if path.duration_days:
            response += f"**Estimated Duration:** {path.duration_days} days\n"

        if ctx['earliest_due'] and ctx['latest_due']:
            response += f"\n**Task Timeline:**\n"
            response += f"• Earliest due: {ctx['earliest_due'].strftime('%b %d, %Y')}\n"
            response += f"• Latest due: {ctx['latest_due'].strftime('%b %d, %Y')}\n"

        return response

    def _response_goal(self, path, ctx):
        """Generate goal/purpose response."""
        response = "🎯 **Goal & Purpose**\n\n"

        response += f"**{path.title}**\n\n"

        if path.goal_statement:
            response += f"**Goal:**\n{path.goal_statement}\n\n"

        if path.project_summary:
            response += f"**Summary:**\n{path.project_summary}\n\n"

        if path.issue:
            response += f"**Addressing Issue:**\n{path.issue.title}\n"
            if path.issue.description:
                response += f"{path.issue.description[:200]}{'...' if len(path.issue.description) > 200 else ''}\n"

        return response

    def _response_issue_chain(self, path, ctx):
        """Generate issue > root cause > initiative chain response."""
        response = "🔗 **Path Origin**\n\n"

        if path.issue:
            response += f"**📢 Issue:** {path.issue.title}\n"
            if path.issue.description:
                response += f"   {path.issue.description[:150]}{'...' if len(path.issue.description) > 150 else ''}\n"
            if path.issue.source_channel:
                response += f"   Source: {path.issue.source_channel}\n"
            if path.issue.feedback_count > 1:
                response += f"   Mentioned in {path.issue.feedback_count} feedback items\n"
            response += "\n"

        if path.root_cause:
            response += f"**🔍 Root Cause:** {path.root_cause.title}\n"
            if path.root_cause.description:
                response += f"   {path.root_cause.description[:150]}{'...' if len(path.root_cause.description) > 150 else ''}\n"
            if path.root_cause.cause_category:
                response += f"   Category: {path.root_cause.cause_category}\n"
            response += "\n"

        if path.initiative:
            response += f"**💡 Initiative:** {path.initiative.title}\n"
            if path.initiative.description:
                response += f"   {path.initiative.description[:150]}{'...' if len(path.initiative.description) > 150 else ''}\n"
            if path.initiative.estimated_effort:
                response += f"   Effort: {path.initiative.estimated_effort}\n"
            if path.initiative.estimated_impact:
                response += f"   Impact: {path.initiative.estimated_impact}\n"

        return response

    def _response_success_factors(self, path, ctx):
        """Generate success factors response."""
        if self._is_completed_or_archived(path):
            response = "🏆 **Success Factors (Retrospective)**\n\n"

            factors = []

            if ctx['completed_actions'] == ctx['total_actions'] and ctx['total_actions'] > 0:
                factors.append(f"✅ **All {ctx['total_actions']} action items completed** — full delivery")
            elif ctx['total_actions'] > 0:
                factors.append(f"✅ **{ctx['completed_actions']}/{ctx['total_actions']} action items completed** ({path.progress_percentage}%)")

            if ctx['completed_phases'] > 0:
                factors.append(f"✅ **{ctx['completed_phases']}/{len(ctx['phases'])} phases completed**")

            if len(ctx['all_assignees']) > 0:
                factors.append(f"👥 **{len(ctx['all_assignees'])} team members** contributed")

            if path.what_was_solved:
                factors.append(f"🎯 **{len(path.what_was_solved)} outcome(s)** achieved")

            if path.key_learnings:
                factors.append(f"📚 **{len(path.key_learnings)} learning(s)** documented for future paths")

            if path.goal_statement:
                factors.append("🎯 **Clear goal was defined** from the start")

            if ctx['days_active'] > 0:
                factors.append(f"📅 **Completed in {ctx['days_active']} days**")

            for factor in factors:
                response += f"• {factor}\n"

            return response

        response = "🏆 **Success Factors**\n\n"

        # Based on path data, identify key success factors
        factors = []

        if ctx['blocked_actions']:
            factors.append(f"⚠️ **Resolve {len(ctx['blocked_actions'])} blocked items** to unblock progress")
        else:
            factors.append("✅ No blocked items - good momentum!")

        if ctx['overdue_actions']:
            factors.append(f"🔴 **Address {len(ctx['overdue_actions'])} overdue tasks** urgently")

        if len(ctx['all_assignees']) > 0:
            factors.append(f"👥 **{len(ctx['all_assignees'])} team members** are engaged")

        if ctx['completed_phases'] > 0:
            factors.append(f"✅ **{ctx['completed_phases']} phases completed** - solid progress")

        if path.progress_percentage >= 75:
            factors.append("🎯 **75%+ complete** - finish line in sight!")
        elif path.progress_percentage >= 50:
            factors.append("📈 **Halfway there** - maintain momentum")

        if path.goal_statement:
            factors.append("🎯 **Clear goal defined** - team knows the target")

        for factor in factors:
            response += f"• {factor}\n"

        response += "\n**Recommendations:**\n"
        if ctx['blocked_actions']:
            response += "• Focus on unblocking stuck tasks first\n"
        if len(ctx['in_progress_actions']) > 5:
            response += "• Consider focusing on fewer tasks at once\n"
        if not ctx['all_assignees']:
            response += "• Assign team members to tasks\n"

        return response

    def _response_improvements(self, path, ctx):
        """Generate improvements/recommendations response."""
        if self._is_completed_or_archived(path):
            response = "💡 **Retrospective Insights**\n\n"

            insights = []

            if path.key_learnings:
                response += "**Key Learnings:**\n"
                for item in path.key_learnings:
                    response += f"• {item}\n"
                response += "\n"

            if path.completed_issues_faced:
                response += "**Challenges Encountered:**\n"
                for item in path.completed_issues_faced:
                    response += f"• {item}\n"
                response += "\n"

            # Retrospective observations
            if ctx['total_actions'] > 0 and ctx['completed_actions'] < ctx['total_actions']:
                insights.append(f"📊 {ctx['total_actions'] - ctx['completed_actions']} action items were not completed — consider reviewing if they are still needed")

            if ctx['blocked_actions']:
                insights.append(f"⚠️ {len(ctx['blocked_actions'])} items remained blocked at completion — worth investigating for future paths")

            if not path.key_learnings:
                insights.append("📝 No learnings documented yet — consider adding retrospective notes for future reference")

            if insights:
                response += "**Suggestions for Future Paths:**\n"
                for insight in insights:
                    response += f"• {insight}\n"
            elif not path.key_learnings and not path.completed_issues_faced:
                response += "✅ This path was completed successfully.\n\n"
                response += "Consider documenting learnings to help future improvement paths."

            return response

        response = "💡 **Recommendations**\n\n"

        recommendations = []

        # Blocked items
        if ctx['blocked_actions']:
            recommendations.append({
                'priority': 'high',
                'text': f"Resolve {len(ctx['blocked_actions'])} blocked tasks to restore momentum"
            })

        # Overdue items
        if ctx['overdue_actions']:
            recommendations.append({
                'priority': 'high',
                'text': f"Address {len(ctx['overdue_actions'])} overdue items or adjust deadlines"
            })

        # Too many in progress
        if len(ctx['in_progress_actions']) > 5:
            recommendations.append({
                'priority': 'medium',
                'text': f"Focus on completing in-progress tasks ({len(ctx['in_progress_actions'])} active) before starting new ones"
            })

        # Unbalanced workload
        if ctx['assignee_workload']:
            workloads = [(name, data['total']) for name, data in ctx['assignee_workload'].items()]
            if workloads:
                max_load = max(w[1] for w in workloads)
                min_load = min(w[1] for w in workloads)
                if max_load > 0 and min_load > 0 and max_load > min_load * 3:
                    recommendations.append({
                        'priority': 'medium',
                        'text': "Consider redistributing tasks - workload appears uneven"
                    })

        # No assignees
        unassigned = [a for a in ctx['in_progress_actions'] + ctx['todo_actions'] if not a['assignee']]
        if unassigned:
            recommendations.append({
                'priority': 'medium',
                'text': f"Assign owners to {len(unassigned)} unassigned tasks"
            })

        # Missing due dates
        no_due_date = [a for a in ctx['todo_actions'] + ctx['in_progress_actions'] if not a['due_date']]
        if len(no_due_date) > ctx['total_actions'] * 0.3:
            recommendations.append({
                'priority': 'low',
                'text': "Add due dates to more tasks for better timeline visibility"
            })

        if not recommendations:
            response += "✅ **This path is well-organized!**\n\n"
            response += "No major improvements needed. Keep up the good work!"
            return response

        # Sort by priority
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        recommendations.sort(key=lambda x: priority_order[x['priority']])

        for rec in recommendations:
            emoji = "🔴" if rec['priority'] == 'high' else "🟡" if rec['priority'] == 'medium' else "🟢"
            response += f"{emoji} {rec['text']}\n\n"

        return response

    def _response_on_hold(self, path, ctx):
        """Generate on-hold information response."""
        response = "⏸️ **On Hold Information**\n\n"

        if path.status != 'on_hold':
            response += f"This path is currently **{path.status.replace('_', ' ').title()}**, not on hold.\n"
            if path.paused_at:
                response += f"\nLast paused: {path.paused_at.strftime('%B %d, %Y')}"
            return response

        if path.paused_at:
            response += f"**Paused on:** {path.paused_at.strftime('%B %d, %Y')}\n\n"

        if path.on_hold_reason:
            response += f"**Reason:**\n{path.on_hold_reason}\n\n"

        if path.what_was_started:
            response += f"**What was started:**\n{path.what_was_started}\n\n"

        if path.on_hold_issues_faced:
            response += f"**Issues faced:**\n{path.on_hold_issues_faced}\n\n"

        response += f"**Progress at pause:** {path.progress_percentage}% ({ctx['completed_actions']}/{ctx['total_actions']} tasks)"

        return response

    def _response_learnings(self, path, ctx):
        """Generate learnings and insights response."""
        response = "📚 **Learnings & Insights**\n\n"

        if path.key_learnings:
            response += "**Key Learnings:**\n"
            for item in path.key_learnings:
                response += f"• {item}\n"
            response += "\n"

        if path.completed_issues_faced:
            response += "**Challenges Overcome:**\n"
            for item in path.completed_issues_faced:
                response += f"• {item}\n"
            response += "\n"

        if not path.key_learnings and not path.completed_issues_faced:
            response += "No learnings have been documented yet.\n\n"

            # Provide insights based on data
            if ctx['blocked_actions']:
                response += f"💡 **Current insight:** {len(ctx['blocked_actions'])} blocked items might reveal process bottlenecks.\n"
            if ctx['completed_phases'] > 0:
                response += f"💡 **Progress insight:** {ctx['completed_phases']} completed phases show good execution.\n"

        return response

    def _response_full_summary(self, path, ctx):
        """Generate a comprehensive summary response."""
        response = f"📋 **Complete Summary: {path.title}**\n\n"

        # Status
        response += f"**Status:** {path.status.replace('_', ' ').title()} | **Progress:** {path.progress_percentage}%\n\n"

        # Goal
        if path.goal_statement:
            response += f"**Goal:** {path.goal_statement[:200]}{'...' if len(path.goal_statement) > 200 else ''}\n\n"

        # Origin
        if path.issue:
            response += f"**Issue:** {path.issue.title}\n"
        if path.root_cause:
            response += f"**Root Cause:** {path.root_cause.title}\n"
        if path.initiative:
            response += f"**Initiative:** {path.initiative.title}\n"
        response += "\n"

        # Progress
        response += f"**Tasks:** {ctx['completed_actions']}/{ctx['total_actions']} done"
        if ctx['blocked_actions']:
            response += f", {len(ctx['blocked_actions'])} blocked"
        response += "\n"

        response += f"**Phases:** {ctx['completed_phases']}/{len(ctx['phases'])} complete\n"
        response += f"**Team:** {len(ctx['all_assignees'])} members\n\n"

        # Timeline
        if path.started_at:
            response += f"**Started:** {path.started_at.strftime('%b %d, %Y')}\n"
        if path.target_completion_date:
            response += f"**Target:** {path.target_completion_date.strftime('%b %d, %Y')}\n"

        return response

    def _response_default(self, path, ctx):
        """Generate default response with helpful suggestions."""
        response = f"🥔 **{path.title}**\n\n"

        if path.project_summary:
            response += f"{path.project_summary[:300]}{'...' if len(path.project_summary) > 300 else ''}\n\n"

        response += f"**Status:** {path.status.replace('_', ' ').title()}\n"
        response += f"**Progress:** {path.progress_percentage}% ({ctx['completed_actions']}/{ctx['total_actions']} tasks)\n"
        response += f"**Team:** {len(ctx['all_assignees'])} members\n\n"

        if self._is_completed_or_archived(path):
            response += "💡 **Ask me about:**\n"
            response += "• Accomplishments & outcomes\n"
            response += "• Success factors\n"
            response += "• Learnings & insights\n"
            response += "• Timeline & duration\n"
            response += "• Team contributions\n"
            response += "• Retrospective insights\n"
            response += "• Full summary"
        else:
            response += "💡 **Ask me about:**\n"
            response += "• Status & progress\n"
            response += "• Blockers & risks\n"
            response += "• Deadlines & timeline\n"
            response += "• Team & workload\n"
            response += "• Phases & steps\n"
            response += "• Goal & purpose\n"
            response += "• Issue & root cause\n"
            response += "• Accomplishments\n"
            response += "• Recommendations\n"
            response += "• Full summary"

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
