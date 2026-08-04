# tasks/models.py
from django.db import models
from categories.models import Department, Role, UserCredential


class TaskAssignment(models.Model):
    TASK_TYPE_CHOICES = (
        ("lead_handling", "Lead Handling"),
    )
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("reassigned", "Reassigned"),   # ← NEW: marks a superseded row in the history chain
    )

    ticket_id = models.CharField(max_length=20, db_index=True)
    task_type = models.CharField(max_length=30, choices=TASK_TYPE_CHOICES, default="lead_handling")

    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="task_assignments")
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, related_name="task_assignments")

    assigned_to = models.ForeignKey(UserCredential, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name="tasks_assigned_to_me")
    # snapshot of the name at assignment time — history stays readable even if the user is later deactivated/deleted
    assigned_to_name = models.CharField(max_length=150, blank=True)

    assigned_by = models.ForeignKey(UserCredential, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name="tasks_assigned_by_me")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    notes = models.TextField(blank=True)

    deadline_hours = models.FloatField(null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)

    assigned_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "tbl_task_assignment"
        ordering = ["-assigned_at"]
        # NOTE: unique_together on (ticket_id, task_type) is REMOVED —
        # each (re)assignment is a new row, so history is never overwritten.
        indexes = [
            models.Index(fields=["ticket_id", "task_type", "-assigned_at"]),
        ]

    def __str__(self):
        return f"{self.ticket_id} → {self.task_type} → {self.assigned_to_name} ({self.status})"
    
    
class AutoAssignRotation(models.Model):
    """Tracks the last person auto-assigned for a (department, role) pair,
    so the NEXT campaign's auto-assignment picks up where the last one left off —
    independent of any single ticket's own reassignment chain."""
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="auto_assign_rotations")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="auto_assign_rotations")
    last_assigned_user = models.ForeignKey(UserCredential, on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tbl_auto_assign_rotation"
        unique_together = ("department", "role")