"""
Path Library Models for Jot Potato.

A Path represents the complete journey from identifying an issue to implementing a solution:
Issue -> Root Cause -> Initiative -> Implementation Plan

Implementation Plan hierarchy:
- Phases (major stages of the plan)
  - Steps (specific activities within a phase)
    - Action Items (individual tasks to complete a step)
"""

import uuid
from django.db import models


class PathStatus(models.TextChoices):
    """Status choices for a Path."""
    ACTIVE = 'active', 'Active'
    ON_HOLD = 'on_hold', 'On Hold'
    COMPLETED = 'completed', 'Completed'
    ARCHIVED = 'archived', 'Archived'


class ItemStatus(models.TextChoices):
    """Status choices for Phases, Steps, and Action Items."""
    TODO = 'todo', 'To Do'
    IN_PROGRESS = 'in_progress', 'In Progress'
    BLOCKED = 'blocked', 'Blocked'
    DONE = 'done', 'Done'


class Priority(models.TextChoices):
    """Priority levels."""
    LOW = 'low', 'Low'
    MEDIUM = 'medium', 'Medium'
    HIGH = 'high', 'High'
    CRITICAL = 'critical', 'Critical'


class BaseModel(models.Model):
    """Abstract base model with common fields."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Issue(BaseModel):
    """
    Problem statement extracted from customer feedback.

    Examples:
    - "The response time is too long"
    - "The staff is unfriendly"
    - "Deliveries are consistently late"
    """
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Source tracking
    source_channel = models.CharField(
        max_length=100,
        blank=True,
        help_text="Where this issue was identified (e.g., Google Reviews, Instagram, Email)"
    )
    feedback_count = models.PositiveIntegerField(
        default=1,
        help_text="Number of feedback items mentioning this issue"
    )

    # Classification
    category = models.CharField(max_length=100, blank=True)
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM
    )
    emotional_intensity = models.PositiveSmallIntegerField(
        default=5,
        help_text="Emotional intensity score (1-10)"
    )

    # Organization reference (for multi-tenant support)
    organization_id = models.UUIDField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization_id', 'category']),
            models.Index(fields=['priority']),
        ]

    def __str__(self):
        return self.title


class RootCause(BaseModel):
    """
    Reason why an issue is happening.
    Can be AI-generated or human input.
    """
    issue = models.ForeignKey(
        Issue,
        on_delete=models.CASCADE,
        related_name='root_causes'
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    is_ai_generated = models.BooleanField(default=False)
    confidence_score = models.FloatField(null=True, blank=True)
    cause_category = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ['-confidence_score', '-created_at']

    def __str__(self):
        return f"{self.title} (for: {self.issue.title[:30]})"


class Initiative(BaseModel):
    """Solution to fix a root cause."""
    root_cause = models.ForeignKey(
        RootCause,
        on_delete=models.CASCADE,
        related_name='initiatives'
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    initiative_type = models.CharField(max_length=50, blank=True)
    estimated_effort = models.CharField(max_length=50, blank=True)
    estimated_impact = models.CharField(max_length=50, blank=True)
    is_ai_generated = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Path(BaseModel):
    """
    A Path is the complete improvement journey.
    All paths in the library are active (implementation has started).
    """
    # The selected chain
    issue = models.ForeignKey(Issue, on_delete=models.PROTECT, related_name='paths')
    root_cause = models.ForeignKey(RootCause, on_delete=models.PROTECT, related_name='paths')
    initiative = models.ForeignKey(Initiative, on_delete=models.PROTECT, related_name='paths')

    # Path metadata
    title = models.CharField(max_length=255)
    goal_statement = models.TextField(blank=True)

    # Status tracking - default is ACTIVE (no drafts)
    status = models.CharField(
        max_length=20,
        choices=PathStatus.choices,
        default=PathStatus.ACTIVE
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM
    )

    # Timeline
    started_at = models.DateTimeField(null=True, blank=True)
    target_completion_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Progress tracking
    progress_percentage = models.PositiveSmallIntegerField(default=0)

    # Impact measurement
    baseline_metric = models.JSONField(null=True, blank=True)
    current_metric = models.JSONField(null=True, blank=True)

    # Organization and ownership
    organization_id = models.UUIDField(null=True, blank=True, db_index=True)
    owner_id = models.UUIDField(null=True, blank=True)

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name_plural = 'Paths'
        indexes = [
            models.Index(fields=['organization_id', 'status']),
            models.Index(fields=['owner_id']),
            models.Index(fields=['status', 'priority']),
        ]

    def __str__(self):
        return self.title

    def calculate_progress(self):
        """Calculate progress based on completed action items across all phases."""
        total_items = 0
        completed_items = 0
        for phase in self.phases.all():
            for step in phase.steps.all():
                items = step.action_items.all()
                total_items += items.count()
                completed_items += items.filter(status=ItemStatus.DONE).count()
        if total_items == 0:
            return 0
        return int((completed_items / total_items) * 100)

    def update_progress(self):
        """Update the progress percentage."""
        self.progress_percentage = self.calculate_progress()
        self.save(update_fields=['progress_percentage', 'updated_at'])


class Phase(BaseModel):
    """
    A major stage in the implementation plan.

    Examples:
    - "Phase 1: Research & Planning"
    - "Phase 2: Implementation"
    - "Phase 3: Training & Rollout"
    """
    path = models.ForeignKey(Path, on_delete=models.CASCADE, related_name='phases')

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=ItemStatus.choices,
        default=ItemStatus.TODO
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"{self.title} ({self.path.title[:20]})"

    def calculate_progress(self):
        """Calculate phase progress based on completed action items."""
        total_items = 0
        completed_items = 0
        for step in self.steps.all():
            items = step.action_items.all()
            total_items += items.count()
            completed_items += items.filter(status=ItemStatus.DONE).count()
        if total_items == 0:
            return 0
        return int((completed_items / total_items) * 100)


class Step(BaseModel):
    """
    A specific activity within a phase.

    Examples for phase "Research & Planning":
    - "Research inventory software options"
    - "Compare vendor pricing"
    - "Get team input on requirements"
    """
    phase = models.ForeignKey(Phase, on_delete=models.CASCADE, related_name='steps')

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=ItemStatus.choices,
        default=ItemStatus.TODO
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return self.title

    def calculate_progress(self):
        """Calculate step progress based on completed action items."""
        items = self.action_items.all()
        if not items.exists():
            return 0
        completed = items.filter(status=ItemStatus.DONE).count()
        return int((completed / items.count()) * 100)


class ActionItem(BaseModel):
    """
    Individual task to complete a step.

    Examples for step "Research inventory software options":
    - "Review MarketMan features and pricing"
    - "Review BlueCart features and pricing"
    - "Review Lightspeed features and pricing"
    - "Create comparison spreadsheet"
    """
    step = models.ForeignKey(Step, on_delete=models.CASCADE, related_name='action_items')

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=ItemStatus.choices,
        default=ItemStatus.TODO
    )
    assignee_id = models.UUIDField(null=True, blank=True)

    order = models.PositiveIntegerField(default=0)
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update path progress when action item is saved
        if self.step_id and self.step.phase_id and self.step.phase.path_id:
            self.step.phase.path.update_progress()


# Keep Task as alias for backward compatibility
Task = ActionItem
TaskStatus = ItemStatus


class PathComment(BaseModel):
    """Comments and updates on a Path for team collaboration."""
    path = models.ForeignKey(Path, on_delete=models.CASCADE, related_name='comments')
    author_id = models.UUIDField()
    content = models.TextField()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Comment on {self.path.title[:30]}"
