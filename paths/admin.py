"""
Django Admin configuration for Path Library models.
"""

from django.contrib import admin
from .models import Issue, RootCause, Initiative, Path, Phase, Step, ActionItem, PathComment


class RootCauseInline(admin.TabularInline):
    model = RootCause
    extra = 0


class InitiativeInline(admin.TabularInline):
    model = Initiative
    extra = 0


class ActionItemInline(admin.TabularInline):
    model = ActionItem
    extra = 0
    fields = ['title', 'status', 'order', 'assignee_id', 'due_date']


class StepInline(admin.TabularInline):
    model = Step
    extra = 0
    fields = ['title', 'status', 'order']


class PhaseInline(admin.TabularInline):
    model = Phase
    extra = 0
    fields = ['title', 'status', 'order']


class PathCommentInline(admin.TabularInline):
    model = PathComment
    extra = 0
    readonly_fields = ['created_at']


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'priority', 'feedback_count', 'source_channel', 'created_at']
    list_filter = ['priority', 'category', 'source_channel']
    search_fields = ['title', 'description']
    inlines = [RootCauseInline]


@admin.register(RootCause)
class RootCauseAdmin(admin.ModelAdmin):
    list_display = ['title', 'issue', 'cause_category', 'is_ai_generated', 'confidence_score']
    list_filter = ['is_ai_generated', 'cause_category']
    search_fields = ['title', 'description']
    inlines = [InitiativeInline]


@admin.register(Initiative)
class InitiativeAdmin(admin.ModelAdmin):
    list_display = ['title', 'root_cause', 'initiative_type', 'estimated_effort', 'estimated_impact']
    list_filter = ['initiative_type', 'estimated_effort', 'estimated_impact', 'is_ai_generated']
    search_fields = ['title', 'description']


@admin.register(Path)
class PathAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'priority', 'progress_percentage', 'owner_id', 'created_at']
    list_filter = ['status', 'priority']
    search_fields = ['title', 'goal_statement', 'notes']
    readonly_fields = ['progress_percentage', 'created_at', 'updated_at']
    inlines = [PhaseInline, PathCommentInline]

    fieldsets = (
        (None, {
            'fields': ('title', 'goal_statement', 'status', 'priority')
        }),
        ('Linked Entities', {
            'fields': ('issue', 'root_cause', 'initiative')
        }),
        ('Timeline', {
            'fields': ('started_at', 'target_completion_date', 'completed_at')
        }),
        ('Progress & Metrics', {
            'fields': ('progress_percentage', 'baseline_metric', 'current_metric')
        }),
        ('Ownership', {
            'fields': ('organization_id', 'owner_id')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Phase)
class PhaseAdmin(admin.ModelAdmin):
    list_display = ['title', 'path', 'status', 'order']
    list_filter = ['status', 'path']
    search_fields = ['title', 'description']
    inlines = [StepInline]


@admin.register(Step)
class StepAdmin(admin.ModelAdmin):
    list_display = ['title', 'phase', 'status', 'order']
    list_filter = ['status', 'phase']
    search_fields = ['title', 'description']
    inlines = [ActionItemInline]


@admin.register(ActionItem)
class ActionItemAdmin(admin.ModelAdmin):
    list_display = ['title', 'step', 'status', 'order', 'assignee_id', 'due_date']
    list_filter = ['status', 'step']
    search_fields = ['title', 'description']


@admin.register(PathComment)
class PathCommentAdmin(admin.ModelAdmin):
    list_display = ['path', 'author_id', 'created_at']
    list_filter = ['path']
    search_fields = ['content']
