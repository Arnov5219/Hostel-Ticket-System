import datetime
from io import StringIO
import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.hostels.models import GenderType, Hostel, Room
from apps.tickets.models import (
    ActivityAction,
    Category,
    CommentScope,
    Priority,
    Status,
    Ticket,
    TicketActivity,
    TicketComment,
    TicketVisibility,
)
from apps.tickets.services.deletion import (
    can_delete,
    generate_undo_token,
    restore,
    soft_delete,
    undo_delete,
)


@pytest.fixture
def deletion_setup(db):
    h1 = Hostel.objects.create(name="Hostel One", code="H1", gender_type=GenderType.BOYS)
    h2 = Hostel.objects.create(name="Hostel Two", code="H2", gender_type=GenderType.BOYS)

    r1 = Room.objects.create(hostel=h1, room_number="101", floor=1, capacity=2)
    r2 = Room.objects.create(hostel=h2, room_number="201", floor=2, capacity=2)

    cat, _ = Category.objects.get_or_create(name="Maintenance", defaults={"is_active": True})

    student1 = User.objects.create_user(
        login_id="std_del_01",
        full_name="Hosteler One",
        role=Role.HOSTELER,
        hostel=h1,
        room=r1,
        residence_set_at=timezone.now(),
        password="password123",
    )
    student2 = User.objects.create_user(
        login_id="std_del_02",
        full_name="Hosteler Two",
        role=Role.HOSTELER,
        hostel=h1,
        room=r1,
        residence_set_at=timezone.now(),
        password="password123",
    )
    warden1 = User.objects.create_user(
        login_id="wrd_del_01",
        full_name="Warden One",
        role=Role.WARDEN,
        hostel=h1,
        password="password123",
    )
    chief_warden = User.objects.create_user(
        login_id="cw_del_01",
        full_name="Chief Warden",
        role=Role.CHIEF_WARDEN,
        password="password123",
    )
    admin_user = User.objects.create_user(
        login_id="adm_del_01",
        full_name="System Admin",
        role=Role.ADMIN,
        password="password123",
    )

    ticket1 = Ticket.objects.create(
        ticket_no="HTL-DEL-001",
        title="Leaky tap in bathroom",
        description="Water leaking from sink tap",
        category=cat,
        reporter=student1,
        hostel=h1,
        room=r1,
        status=Status.OPEN,
        priority=Priority.MEDIUM,
    )

    return {
        "h1": h1,
        "h2": h2,
        "r1": r1,
        "cat": cat,
        "student1": student1,
        "student2": student2,
        "warden1": warden1,
        "chief_warden": chief_warden,
        "admin": admin_user,
        "ticket1": ticket1,
    }


@pytest.mark.django_db
class TestCanDeleteRules:
    def test_hosteler_own_open_ticket_allowed(self, deletion_setup):
        s1 = deletion_setup["student1"]
        t1 = deletion_setup["ticket1"]
        allowed, reason = can_delete(s1, t1)
        assert allowed is True
        assert reason == ""

    def test_hosteler_other_ticket_denied(self, deletion_setup):
        s2 = deletion_setup["student2"]
        t1 = deletion_setup["ticket1"]
        allowed, reason = can_delete(s2, t1)
        assert allowed is False
        assert "reported" in reason

    def test_hosteler_in_progress_denied(self, deletion_setup):
        s1 = deletion_setup["student1"]
        t1 = deletion_setup["ticket1"]
        t1.status = Status.IN_PROGRESS
        t1.save()
        allowed, reason = can_delete(s1, t1)
        assert allowed is False
        assert "in progress" in reason.lower()

    def test_hosteler_reposted_ticket_denied(self, deletion_setup):
        s1 = deletion_setup["student1"]
        t1 = deletion_setup["ticket1"]
        t1.repost_count = 1
        t1.save()
        allowed, reason = can_delete(s1, t1)
        assert allowed is False
        assert "reposted" in reason

    def test_hosteler_staff_comment_denied(self, deletion_setup):
        s1 = deletion_setup["student1"]
        w1 = deletion_setup["warden1"]
        t1 = deletion_setup["ticket1"]
        TicketComment.objects.create(
            ticket=t1,
            author=w1,
            body="Looking into this right now.",
            scope=CommentScope.PRIVATE,
        )
        allowed, reason = can_delete(s1, t1)
        assert allowed is False
        assert "commented" in reason.lower()

    def test_warden_own_hostel_allowed(self, deletion_setup):
        w1 = deletion_setup["warden1"]
        t1 = deletion_setup["ticket1"]
        allowed, reason = can_delete(w1, t1)
        assert allowed is True

    def test_warden_other_hostel_denied(self, deletion_setup):
        h2 = deletion_setup["h2"]
        w1 = deletion_setup["warden1"]
        t1 = deletion_setup["ticket1"]
        t1.hostel = h2
        t1.save()
        allowed, reason = can_delete(w1, t1)
        assert allowed is False
        assert "own hostel" in reason

    def test_chief_warden_and_admin_allowed(self, deletion_setup):
        cw = deletion_setup["chief_warden"]
        adm = deletion_setup["admin"]
        t1 = deletion_setup["ticket1"]
        assert can_delete(cw, t1)[0] is True
        assert can_delete(adm, t1)[0] is True


@pytest.mark.django_db
class TestSoftDeleteAndRestoreService:
    def test_hosteler_soft_delete_and_activity(self, deletion_setup):
        s1 = deletion_setup["student1"]
        t1 = deletion_setup["ticket1"]
        soft_delete(t1, s1)
        t1.refresh_from_db()

        assert t1.is_deleted is True
        assert t1.deleted_by == s1
        assert t1.deleted_at is not None
        assert TicketActivity.objects.filter(ticket=t1, action=ActivityAction.DELETED).exists()

    def test_staff_delete_requires_reason(self, deletion_setup):
        w1 = deletion_setup["warden1"]
        t1 = deletion_setup["ticket1"]
        with pytest.raises(ValidationError) as exc:
            soft_delete(t1, w1, reason="bad")
        assert "at least 5 characters" in str(exc.value)

        soft_delete(t1, w1, reason="Duplicate ticket submitted")
        t1.refresh_from_db()
        assert t1.is_deleted is True
        assert t1.delete_reason == "Duplicate ticket submitted"

    def test_undo_delete_with_valid_token(self, deletion_setup):
        s1 = deletion_setup["student1"]
        t1 = deletion_setup["ticket1"]
        soft_delete(t1, s1)
        token = generate_undo_token(t1.ticket_no, s1.id)

        undo_delete(t1.ticket_no, s1, token)
        t1.refresh_from_db()
        assert t1.is_deleted is False
        assert t1.deleted_at is None
        assert t1.deleted_by is None
        assert TicketActivity.objects.filter(ticket=t1, action=ActivityAction.RESTORED).exists()

    def test_undo_delete_wrong_user_fails(self, deletion_setup):
        s1 = deletion_setup["student1"]
        s2 = deletion_setup["student2"]
        t1 = deletion_setup["ticket1"]
        soft_delete(t1, s1)
        token = generate_undo_token(t1.ticket_no, s1.id)

        with pytest.raises(ValidationError):
            undo_delete(t1.ticket_no, s2, token)

    def test_admin_restore(self, deletion_setup):
        adm = deletion_setup["admin"]
        w1 = deletion_setup["warden1"]
        t1 = deletion_setup["ticket1"]
        soft_delete(t1, w1, reason="Test delete reason")

        with pytest.raises(ValidationError):
            restore(t1, w1)

        restore(t1, adm)
        t1.refresh_from_db()
        assert t1.is_deleted is False
        assert t1.deleted_at is None
        assert t1.delete_reason == ""


@pytest.mark.django_db
class TestTicketQueriesExcludeDeleted:
    def test_active_manager_filters_deleted(self, deletion_setup):
        s1 = deletion_setup["student1"]
        t1 = deletion_setup["ticket1"]
        assert Ticket.objects.filter(ticket_no=t1.ticket_no).exists()

        soft_delete(t1, s1)
        assert not Ticket.objects.filter(ticket_no=t1.ticket_no).exists()
        assert Ticket.all_objects.filter(ticket_no=t1.ticket_no).exists()

    def test_list_and_trash_views(self, client, deletion_setup):
        s1 = deletion_setup["student1"]
        w1 = deletion_setup["warden1"]
        adm = deletion_setup["admin"]
        t1 = deletion_setup["ticket1"]

        client.force_login(s1)
        res = client.get(reverse("tickets:list"))
        assert t1.ticket_no in res.content.decode()

        # Delete ticket
        soft_delete(t1, s1)

        # Ticket should not appear in active list
        res = client.get(reverse("tickets:list"))
        assert t1.ticket_no not in res.content.decode()

        # Hosteler cannot access trash
        res_trash = client.get(reverse("tickets:trash"))
        assert res_trash.status_code == 403

        # Warden can view trash
        client.force_login(w1)
        res_warden_trash = client.get(reverse("tickets:trash"))
        assert res_warden_trash.status_code == 200
        assert t1.ticket_no in res_warden_trash.content.decode()

        # Admin can view trash and restore
        client.force_login(adm)
        res_restore = client.post(reverse("tickets:restore", kwargs={"ticket_no": t1.ticket_no}))
        assert res_restore.status_code in (200, 302)
        t1.refresh_from_db()
        assert t1.is_deleted is False


@pytest.mark.django_db
class TestPurgeDeletedCommand:
    def test_purge_command_dry_run_and_confirm(self, deletion_setup):
        s1 = deletion_setup["student1"]
        t1 = deletion_setup["ticket1"]
        soft_delete(t1, s1)

        # Simulate deleted 100 days ago
        old_time = timezone.now() - datetime.timedelta(days=100)
        Ticket.all_objects.filter(id=t1.id).update(deleted_at=old_time)

        out = StringIO()
        call_command("purge_deleted", stdout=out)
        output = out.getvalue()
        assert "Dry run" in output
        assert Ticket.all_objects.filter(id=t1.id).exists()

        # Run with confirm
        out_confirm = StringIO()
        call_command("purge_deleted", "--confirm", stdout=out_confirm)
        output_confirm = out_confirm.getvalue()
        assert "Successfully purged 1" in output_confirm
        assert not Ticket.all_objects.filter(id=t1.id).exists()
