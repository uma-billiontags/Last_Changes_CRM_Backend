import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from categories.models import Department, Role, UserCredential
from .models import TaskAssignment
from .serializers import TaskAssignmentSerializer


@require_GET
def get_department_users(request, department_title):
    """Returns roles -> nested active users for a given department (e.g. 'Account Manager')."""
    try:
        department = Department.objects.get(title__iexact=department_title, is_active=True)
    except Department.DoesNotExist:
        return JsonResponse({"error": f"Department '{department_title}' not found."}, status=404)

    roles = Role.objects.filter(department=department, is_active=True).order_by("title")

    data = []
    for role in roles:
        users = UserCredential.objects.filter(role=role, is_active=True).order_by("username")
        if users.exists():  # skip roles with no active users, keeps the picker clean
            data.append({
                "role_id": role.id,
                "role_title": role.title,
                "users": [{"id": u.id, "username": u.username, "email": u.email} for u in users],
            })

    return JsonResponse(data, safe=False)


@require_GET
def get_assignments_for_tickets(request):
    """Bulk-fetch current assignments for a list of ticket_ids (used by the Leads table)."""
    ticket_ids = [t.strip() for t in request.GET.get("ticket_ids", "").split(",") if t.strip()]
    task_type = request.GET.get("task_type", "lead_handling")

    if not ticket_ids:
        return JsonResponse([], safe=False)

    tasks = get_current_assignments_qs(task_type=task_type).filter(ticket_id__in=ticket_ids)
    return JsonResponse(TaskAssignmentSerializer(tasks, many=True).data, safe=False)

from leads.models import Lead
from leads.serializers import LeadSerializer
from campaigns.models import Campaign   # ← ADD THIS

@require_GET
def get_my_leads(request):
    """
    Returns leads currently assigned to a specific user (for their dashboard).
    GET /tasks/get_my_leads/?user_id=5&task_type=lead_handling
    """
    user_id = request.GET.get("user_id")
    task_type = request.GET.get("task_type", "lead_handling")

    if not user_id:
        return JsonResponse({"error": "user_id is required."}, status=400)

    assigned_tasks = get_current_assignments_qs(task_type=task_type).filter(
    assigned_to_id=user_id
    ).exclude(status="cancelled")
    
    ticket_ids = list(assigned_tasks.values_list("ticket_id", flat=True))
    if not ticket_ids:
        return JsonResponse([], safe=False)

    leads = Lead.objects.filter(ticket_id__in=ticket_ids).order_by("-received_at")
    serializer = LeadSerializer(leads, many=True, context={"request": request})

    # ── which of these tickets already have a campaign ──
    campaigned_tickets = set(
        Campaign.objects.filter(ticket_id__in=ticket_ids)
        .values_list("ticket_id", flat=True)
    )   # ← ADD THIS

    # attach each lead's task status/assigned_at so the dashboard can show it
    status_map = {t.ticket_id: t for t in assigned_tasks}
    data = serializer.data
    for lead_data in data:
        task = status_map.get(lead_data.get("ticket_id"))
        lead_data["task_status"] = task.status if task else None
        lead_data["assigned_at"] = task.assigned_at.isoformat() if task else None
        lead_data["has_campaign"] = lead_data.get("ticket_id") in campaigned_tickets   # ← ADD THIS

    return JsonResponse(data, safe=False)


#-----------------------NEW-----------------------------------------
# round_robin
from categories.models import UserCredential

BUSY_THRESHOLD = 3  # 3 or more active tasks = busy


def get_next_assignee(role, current_user, ticket_id=None, task_type=None):
    """
    Walks the role's active users in alphabetical (username) order, starting
    right after `current_user`, wrapping around. Returns the first person found
    with fewer than BUSY_THRESHOLD active tasks.

    Order is ALWAYS alphabetical — busy people are skipped, not reordered.
    Example: Arun, Babu, Chandra, David, Guna, Hari — current=Chandra, and
    David is busy → checks David (skip), Guna (skip if busy), Hari, Arun, Babu...

    Returns None if everyone in the role is busy (caller should leave the
    ticket with its current holder rather than force an overload).
    """
    users = list(
        UserCredential.objects.filter(role=role, is_active=True).order_by("username")
    )
    if not users:
        return None

    if current_user is None:
        start_idx = -1  # so the loop below starts at index 0
    else:
        ids = [u.id for u in users]
        try:
            start_idx = ids.index(current_user.id)
        except ValueError:
            start_idx = -1  # current holder no longer active/in role — start from the top

    n = len(users)
    for step in range(1, n + 1):
        candidate = users[(start_idx + step) % n]
        if candidate.id == (current_user.id if current_user else None):
            continue  # don't hand it right back to the same person
        load = get_active_task_count(candidate, exclude_ticket_id=ticket_id, exclude_task_type=task_type)
        if load < BUSY_THRESHOLD:
            return candidate

    return None  # everyone's busy — leave as-is


# tasks/queries.py
from django.db.models import Max
from .models import TaskAssignment


def get_current_assignment(ticket_id, task_type="lead_handling"):
    """The latest assignment row for a ticket — i.e. 'who has it right now'."""
    return (
        TaskAssignment.objects
        .filter(ticket_id=ticket_id, task_type=task_type)
        .order_by("-assigned_at", "-id")
        .first()
    )


# tasks/queries.py
def get_current_assignments_qs(task_type=None):
    """
    One row per (ticket_id, task_type) — the latest row in each chain.
    Pass task_type to scope to one department (e.g. "lead_handling" for the
    leads dashboard); leave it None to get the current row for EVERY
    department across EVERY ticket (needed by the overdue sweep, which must
    check creative_ops, campaign_ops, etc. — not just lead_handling).
    """
    qs = TaskAssignment.objects.all()
    if task_type:
        qs = qs.filter(task_type=task_type)

    latest_ids = (
        qs.values("ticket_id", "task_type")
        .annotate(latest_id=Max("id"))
        .values_list("latest_id", flat=True)
    )
    return TaskAssignment.objects.filter(id__in=latest_ids)

def get_ticket_history(ticket_id, task_type="lead_handling"):
    """Full chain, oldest → newest, for an audit trail view."""
    return (
        TaskAssignment.objects
        .filter(ticket_id=ticket_id, task_type=task_type)
        .order_by("assigned_at", "id")
    )
    
    
# tasks/views.py
import json
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from categories.models import Role, UserCredential
from .models import TaskAssignment
from .serializers import TaskAssignmentSerializer

@csrf_exempt
@require_POST
def assign_task(request):
    """
    POST /tasks/assign_task/
    Body: { ticket_id, task_type, role_id, user_id (optional), assigned_by_id, deadline_hours }

    - If user_id is given → manual assignment to that person (still validated against role_id).
    - If user_id is omitted → auto-picks the next person alphabetically after whoever
      currently holds the ticket (or the first person alphabetically if it's brand new).
    - The previous current row (if any and still open) is marked 'reassigned' — never deleted/overwritten.
    - A brand new row is always inserted — this IS the history.
    """
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid request body."}, status=400)

    ticket_id = payload.get("ticket_id")
    task_type = payload.get("task_type", "lead_handling")
    role_id = payload.get("role_id")
    user_id = payload.get("user_id")            # optional now
    assigned_by_id = payload.get("assigned_by_id")
    deadline_hours = payload.get("deadline_hours")

    if not ticket_id or not role_id:
        return JsonResponse({"error": "ticket_id and role_id are required."}, status=400)

    try:
        role = Role.objects.select_related("department").get(pk=role_id)
    except Role.DoesNotExist:
        return JsonResponse({"error": "Invalid role."}, status=400)

    previous = get_current_assignment(ticket_id, task_type)

    if user_id:
        try:
            assigned_to = UserCredential.objects.get(pk=user_id, role=role, is_active=True)
        except UserCredential.DoesNotExist:
            return JsonResponse({"error": "Selected user does not belong to the selected role."}, status=400)
    else:
        current_user = previous.assigned_to if previous else None
        assigned_to = get_next_assignee(role, current_user, ticket_id=ticket_id, task_type=task_type)
        if not assigned_to:
            return JsonResponse(
                {"error": "Everyone in this role currently has 3 or more active tasks. Try again later or assign manually."},
                status=409,
            )
            
    assigned_by = UserCredential.objects.filter(pk=assigned_by_id).first() if assigned_by_id else None

    now = timezone.now()
    due_at = now + timezone.timedelta(hours=deadline_hours) if deadline_hours else None

    # close out the previous chain link, if one exists and is still open
    if previous and previous.status in ("pending", "in_progress"):
        previous.status = "reassigned"
        previous.save(update_fields=["status", "updated_at"])

    task = TaskAssignment.objects.create(
        ticket_id=ticket_id,
        task_type=task_type,
        department=role.department,
        role=role,
        assigned_to=assigned_to,
        assigned_to_name=assigned_to.username,
        assigned_by=assigned_by,
        status="pending",
        deadline_hours=deadline_hours,
        due_at=due_at,
    )
    
    # ── Push notification to whoever just got assigned this task ──
    from notifications.notification import send_notification_to_user
    # send_notification_to_user(
    #     user=assigned_to,
    #     title="New task assigned",
    #     body=f"Ticket {ticket_id} — {role.title} — due in {deadline_hours}h" if deadline_hours
    #         else f"Ticket {ticket_id} — {role.title}",
    # )
    
    send_notification_to_user(
    user=assigned_to,
    title=f"New task: {role.department.title}",
    body=f"{ticket_id} · {role.title} · assigned by {assigned_by.username if assigned_by else 'System'}"
         + (f" · due in {deadline_hours}h" if deadline_hours else ""),
)

    return JsonResponse(TaskAssignmentSerializer(task).data, status=201)



@csrf_exempt
@require_POST
def mark_task_complete(request, task_id):
    """
    POST /tasks/mark_task_complete/<task_id>/
    Marks the CURRENT row completed in place — completion is a terminal state,
    not a reassignment, so it doesn't need a new history row.
    """
    try:
        task = TaskAssignment.objects.get(pk=task_id)
    except TaskAssignment.DoesNotExist:
        return JsonResponse({"error": "Task not found."}, status=404)

    task.status = "completed"
    task.completed_at = timezone.now()
    task.save(update_fields=["status", "completed_at", "updated_at"])

    return JsonResponse(TaskAssignmentSerializer(task).data, status=200)

# tasks/tasks.py
from celery import shared_task
from django.utils import timezone

from .models import TaskAssignment

@shared_task
def reassign_overdue_tasks():
    """
    Runs every 5 min via Celery Beat.
    Finds the CURRENT (latest) row for every ticket that's overdue and still open,
    closes it out as 'reassigned', and inserts a brand new row for the next
    person in alphabetical order within that role. Nothing is ever overwritten.
    """
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
            continue  # everyone in the role has 3+ active tasks — leave it, retry next run

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
            assigned_by=None,           # system-triggered
            status="pending",
            deadline_hours=task.deadline_hours,
            due_at=due_at,
            notes="Auto-reassigned (overdue) — round robin",
        )
        reassigned_count += 1

    return (f"Checked {overdue.count()} overdue tasks, reassigned {reassigned_count}, "
            f"{skipped_all_busy} skipped (everyone in role busy).")

# tasks/views.py (add)
from django.views.decorators.http import require_GET

@require_GET
def get_ticket_task_history(request, ticket_id):
    """
    GET /tasks/get_ticket_task_history/<ticket_id>/?task_type=lead_handling
    Full chain of every person who has ever held this ticket, oldest → newest.
    """
    task_type = request.GET.get("task_type", "lead_handling")
    history = get_ticket_history(ticket_id, task_type)
    return JsonResponse(TaskAssignmentSerializer(history, many=True).data, safe=False)

# tasks/queries.py  (add this)
def get_active_task_count(user, exclude_ticket_id=None, exclude_task_type=None):
    """
    How many tickets this person currently holds that are still open (pending/in_progress).
    Used to decide if they're 'busy' (>=3) or 'free' (<3).
    """
    qs = get_current_assignments_qs().filter(
        assigned_to=user,
        status__in=["pending", "in_progress"],
    )
    if exclude_ticket_id:
        qs = qs.exclude(ticket_id=exclude_ticket_id, task_type=exclude_task_type)
    return qs.count()


@require_GET
def get_assignment_history_for_tickets(request):
    """
    GET /tasks/get_assignment_history_for_tickets/?ticket_ids=TIK0001,TIK0002

    Returns, for every ticket, the FULL assignment history grouped by department
    (task_type) — every past assignment + the current one, oldest → newest.
    This is what powers the "Assigned Members" excel-style column: 2 shown inline,
    the rest behind "more…".

    {
      "TIK0001": {
        "creative_ops": [
          {"id": 12, "role_title": "Designer", "assigned_to_name": "arjun",
           "assigned_at": "...", "due_at": "...", "status": "reassigned"},
          {"id": 19, "role_title": "Designer", "assigned_to_name": "kavya",
           "assigned_at": "...", "due_at": "...", "status": "pending"}
        ],
        "campaign_ops": [ ... ]
      }
    }
    """
    ticket_ids = [t.strip() for t in request.GET.get("ticket_ids", "").split(",") if t.strip()]
    if not ticket_ids:
        return JsonResponse({}, safe=False)

    rows = (
        TaskAssignment.objects
        .filter(ticket_id__in=ticket_ids)
        .select_related("role")
        .order_by("ticket_id", "task_type", "assigned_at", "id")
    )

    result: dict = {}
    for row in rows:
        result.setdefault(row.ticket_id, {}).setdefault(row.task_type, []).append({
            "id": row.id,
            "role_title": row.role.title if row.role else None,
            "assigned_to_name": row.assigned_to_name,
            "assigned_at": row.assigned_at.isoformat() if row.assigned_at else None,
            "due_at": row.due_at.isoformat() if row.due_at else None,
            "status": row.status,
        })

    return JsonResponse(result, safe=False)

from django.db.models import Q, F

@require_GET
def get_status_report(request):
    """
    GET /tasks/get_status_report/?status=completed
    GET /tasks/get_status_report/?status=overdue

    completed → every row a user finished (status='completed')
    overdue   → rows that blew their deadline:
                  a) closed out as 'reassigned' because the sweeper moved it, OR
                  b) still open (pending/in_progress) but past due_at right now
                  
    Optional: &user_id=5        ← only that person's rows (for personal dashboards)
    Optional: &task_type=creative_ops   ← only that department's rows
    """
    report_type = request.GET.get("status", "completed")
    user_id = request.GET.get("user_id")          # ← ADD
    task_type = request.GET.get("task_type")      # ← ADD
    now = timezone.now()

    if report_type == "completed":
        rows = TaskAssignment.objects.filter(status="completed")
    elif report_type == "overdue":
        rows = TaskAssignment.objects.filter(
            Q(status="reassigned", due_at__isnull=False, updated_at__gt=F("due_at")) |
            Q(status__in=["pending", "in_progress"], due_at__lt=now)
        )
    else:
        return JsonResponse({"error": "status must be 'completed' or 'overdue'"}, status=400)
    
    if user_id:                                   # ← ADD
        rows = rows.filter(assigned_to_id=user_id)
    if task_type:                                 # ← ADD
        rows = rows.filter(task_type=task_type)

    rows = rows.select_related("role", "department").order_by("-updated_at")

    data = []
    for r in rows:
        if report_type == "overdue":
            if r.status == "reassigned":
                reason = "Deadline missed — auto-reassigned to next person"
            else:
                reason = "Deadline passed — task still open"
        else:
            reason = None

        data.append({
            "id": r.id,
            "ticket_id": r.ticket_id,
            "task_type": r.task_type,
            "department_title": r.department.title if r.department else None,
            "role_title": r.role.title if r.role else None,
            "role_id": r.role_id,
            "assigned_to_name": r.assigned_to_name,
            "status": r.status,
            "assigned_at": r.assigned_at.isoformat() if r.assigned_at else None,
            "due_at": r.due_at.isoformat() if r.due_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "reason": reason,
        })

    return JsonResponse(data, safe=False)

import re
from django.utils import timezone
from categories.models import Department, Role
from .models import TaskAssignment, AutoAssignRotation

AUTO_ASSIGN_DEADLINE_HOURS = 0.1667  # 10 minutes — TEMP, change here later

AUTO_ASSIGN_CONFIG = {
    "Campaign Ops": "Account Director",
    "Creative Ops": "Account Director",
    "Ad Ops": "Account Director",
}

def department_to_task_type(title: str) -> str:
    """Mirrors the frontend's departmentToTaskType() exactly, so task_type
    slugs match what All_Campaigns.tsx looks up in assignment history."""
    slug = re.sub(r'[^a-z0-9]+', '_', title.strip().lower())
    return slug.strip('_')


def auto_assign_campaign_tasks(ticket_id):
    """Call this once, right after a Campaign is created and has a ticket_id.
    Auto-assigns Campaign Ops / Creative Ops / Ad Ops via round robin.
    Never raises — a misconfigured role or an all-busy team just gets skipped,
    so it can't block campaign creation."""
    for dept_title, role_title in AUTO_ASSIGN_CONFIG.items():
        try:
            department = Department.objects.get(title=dept_title, is_active=True)
            role = Role.objects.get(department=department, title=role_title, is_active=True)
        except (Department.DoesNotExist, Role.DoesNotExist):
            continue

        task_type = department_to_task_type(dept_title)

        if get_current_assignment(ticket_id, task_type):
            continue  # already has an assignment somehow — don't double-assign

        rotation, _ = AutoAssignRotation.objects.get_or_create(department=department, role=role)

        next_user = get_next_assignee(
            role, rotation.last_assigned_user,
            ticket_id=ticket_id, task_type=task_type,
        )
        if not next_user:
            continue  # everyone in this role is at BUSY_THRESHOLD — leave unassigned

        now = timezone.now()
        TaskAssignment.objects.create(
            ticket_id=ticket_id,
            task_type=task_type,
            department=department,
            role=role,
            assigned_to=next_user,
            assigned_to_name=next_user.username,
            assigned_by=None,  # system-triggered, like the overdue sweep
            status="pending",
            deadline_hours=AUTO_ASSIGN_DEADLINE_HOURS,
            due_at=now + timezone.timedelta(hours=AUTO_ASSIGN_DEADLINE_HOURS),
            notes="Auto-assigned on campaign creation — round robin",
        )

        rotation.last_assigned_user = next_user
        rotation.save(update_fields=["last_assigned_user", "updated_at"])