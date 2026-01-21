"""
Path Library Models for Jot Potato.

A Path represents the complete journey from identifying an issue to implementing a solution:
Issue -> Root Cause -> Initiative -> Implementation Plan (with Tasks)
"""

import uuid
from django.db import models


class PathStatus(models.TextChoices):
    """Status choices for a Path."""
    DRAFT = 'draft', 'Draft'
    ACTIVE = 'active', 'Active'
    ON_HOLD = 'on_hold', 'On Hold'
    COMPLETED = 'completed', 'Completed'
    ARCHIVED = 'archived', 'Archived'


class TaskStatus(models.TextChoices):
    """Status choices for a Task."""
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

    Examples for issue "Response time is too long":
    - "Not enough staff"
    - "No proper process, team is disorganized"
    - "Lack of communication"
    """
    issue = models.ForeignKey(
        Issue,
        on_delete=models.CASCADE,
        related_name='root_causes'
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Source of the root cause
    is_ai_generated = models.BooleanField(
        default=False,
        help_text="Whether this was suggested by AI"
    )
    confidence_score = models.FloatField(
        null=True,
        blank=True,
        help_text="AI confidence score (0-1)"
    )

    # Fishbone/Ishikawa diagram category
    cause_category = models.CharField(
        max_length=50,
        blank=True,
        help_text="Category in root cause analysis (e.g., People, Process, Tools, Environment)"
    )

    class Meta:
        ordering = ['-confidence_score', '-created_at']

    def __str__(self):
        return f"{self.title} (for: {self.issue.title[:30]})"


class Initiative(BaseModel):
    """
    Solution to fix a root cause.

    Examples for root cause "No proper process, team is disorganized":
    - "Clarify roles & responsibilities"
    - "Build a team onboarding kit"
    - "Monitor Team Performance"
    """
    root_cause = models.ForeignKey(
        RootCause,
        on_delete=models.CASCADE,
        related_name='initiatives'
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Classification
    initiative_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="Type of fix (e.g., quick_win, process_change, training, tool_implementation)"
    )
    estimated_effort = models.CharField(
        max_length=50,
        blank=True,
        help_text="Estimated effort (e.g., small, medium, large)"
    )
    estimated_impact = models.CharField(
        max_length=50,
        blank=True,
        help_text="Expected impact (e.g., low, medium, high)"
    )

    # AI suggestions
    is_ai_generated = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Path(BaseModel):
    """
    A Path is the complete improvement journey.

    It connects: Issue -> Root Cause -> Initiative -> Implementation Plan

    Paths are stored in the Path Library and can be:
    - Active (being worked on)
    - On Hold (paused)
    - Completed (done)
    - Archived (no longer relevant)
    """
    # The selected chain
    issue = models.ForeignKey(
        Issue,
        on_delete=models.PROTECT,
        related_name='paths'
    )
    root_cause = models.ForeignKey(
        RootCause,
        on_delete=models.PROTECT,
        related_name='paths'
    )
    initiative = models.ForeignKey(
        Initiative,
        on_delete=models.PROTECT,
        related_name='paths'
    )

    # Path metadata
    title = models.CharField(
        max_length=255,
        help_text="Custom title for this path"
    )
    goal_statement = models.TextField(
        blank=True,
        help_text="e.g., 'My path to success will improve customer satisfaction to increase growth and revenue'"
    )

    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=PathStatus.choices,
        default=PathStatus.DRAFT
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
    progress_percentage = models.PositiveSmallIntegerField(
        default=0,
        help_text="Completion percentage (0-100)"
    )

    # Impact measurement
    baseline_metric = models.JSONField(
        null=True,
        blank=True,
        help_text="Baseline measurements before starting"
    )
    current_metric = models.JSONField(
        null=True,
        blank=True,
        help_text="Current measurements for comparison"
    )

    # Organization and ownership
    organization_id = models.UUIDField(null=True, blank=True, db_index=True)
    owner_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="User who owns this path"
    )

    # Notes
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
        """Calculate progress based on completed tasks."""
        tasks = self.tasks.all()
        if not tasks.exists():
            return 0
        completed = tasks.filter(status=TaskStatus.DONE).count()
        return int((completed / tasks.count()) * 100)

    def update_progress(self):
        """Update the progress percentage."""
        self.progress_percentage = self.calculate_progress()
        self.save(update_fields=['progress_percentage', 'updated_at'])


class Task(BaseModel):
    """
    Individual task within a Path's implementation plan.

    Examples for initiative "Clarify roles & responsibilities":
    - "Define Success Criteria for roles"
    - "Document ownership"
    - "Map responsibilities for roles"
    """
    path = models.ForeignKey(
        Path,
        on_delete=models.CASCADE,
        related_name='tasks'
    )

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Status and assignment
    status = models.CharField(
        max_length=20,
        choices=TaskStatus.choices,
        default=TaskStatus.TODO
    )
    assignee_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="User assigned to this task"
    )

    # Ordering and hierarchy
    order = models.PositiveIntegerField(default=0)
    parent_task = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subtasks'
    )

    # Timeline
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Notes
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update path progress when task is saved
        if self.path_id:
            self.path.update_progress()


class PathComment(BaseModel):
    """Comments and updates on a Path for team collaboration."""
    path = models.ForeignKey(
        Path,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    author_id = models.UUIDField(help_text="User who wrote the comment")
    content = models.TextField()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Comment on {self.path.title[:30]}"
