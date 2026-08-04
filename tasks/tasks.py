# Added by charu

# tasks/tasks.py
from celery import shared_task
from django.utils import timezone

from .models import TaskAssignment

@shared_task
def reassign_overdue_tasks():
    now = timezone.now()

    overdue = get_current_assignments_qs().filter(
        due_at__lt=now,
        status__in=["pending", "in_progress"],
        role__isnull=False,
    )

    reassigned_count = 0
    skipped_all_busy = 0

    for task in overdue:
        next_person = get_next_assignee(
            task.role, task.assigned_to,
            ticket_id=task.ticket_id, task_type=task.task_type,
            )
        if not next_person:
            skipped_all_busy += 1
            continue

        # close out the old link
        task.status = "reassigned"
        task.save(update_fields=["status", "updated_at"])

        due_at = now + timezone.timedelta(hours=task.deadline_hours) if task.deadline_hours else None

        TaskAssignment.objects.create(
            ticket_id=task.ticket_id,
            task_type=task.task_type,
            department=task.department,
            role=task.role,
            assigned_to=next_person,
            assigned_to_name=next_person.username,
            assigned_by=None,
            status="pending",
            deadline_hours=task.deadline_hours,
            due_at=due_at,
            notes="Auto-reassigned (overdue) — round robin",
        )
        reassigned_count += 1

        # ← INSERT HERE, right after the create() call above
        from notifications.notification import send_notification_to_user
        send_notification_to_user(
            user=next_person,
            title="Task auto-reassigned to you",
            body=f"Ticket {task.ticket_id} — {task.role.title} — previous assignee missed the deadline",
        )

    return (f"Checked {overdue.count()} overdue tasks, reassigned {reassigned_count}, "
            f"{skipped_all_busy} skipped (everyone in role busy).")