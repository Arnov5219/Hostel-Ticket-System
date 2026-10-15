import random
from datetime import timedelta

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import ResidenceHistory, Role, Theme, User
from apps.announcements.models import (
    Announcement,
    AnnouncementKind,
    AnnouncementRead,
    AnnouncementSeverity,
    AnnouncementStatus,
)
from apps.hostels.models import Hostel
from apps.tickets.models import (
    ActivityAction,
    Category,
    Priority,
    RoutingRule,
    Status,
    Ticket,
    TicketActivity,
    TicketComment,
)
from apps.tickets.services.deletion import soft_delete


class Command(BaseCommand):
    help = "Seeds comprehensive demo data: 12 hostels, 1,440 rooms, users, routing rules, and 60 realistic tickets"

    def handle(self, *args, **options):
        self.stdout.write("Starting comprehensive demo data seeding...")

        # 1. Seed Real 12 Hostels and 1,440 Rooms
        call_command("seed_hostels")

        all_hostels = list(Hostel.objects.filter(is_active=True).order_by("code"))
        hostel_a = Hostel.objects.filter(code="BH-1").first() or all_hostels[0]
        hostel_b = Hostel.objects.filter(code="BH-2").first() or all_hostels[1]

        rooms_a = list(hostel_a.rooms.filter(is_active=True).order_by("floor", "room_number"))
        rooms_b = list(hostel_b.rooms.filter(is_active=True).order_by("floor", "room_number"))

        self.stdout.write("Hostel structure initialized (12 hostels, 1,440 rooms).")

        # 3. Seed Users
        # Admin
        admin_user, _ = User.objects.get_or_create(
            login_id="admin",
            defaults={
                "full_name": "System Administrator",
                "role": Role.ADMIN,
                "escalation_level": 4,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        admin_user.set_password("admin123")
        admin_user.theme = Theme.DARK
        admin_user.save()

        # Chief Warden
        chief_warden, _ = User.objects.get_or_create(
            login_id="chief_warden",
            defaults={
                "full_name": "Prof. S. K. Sharma",
                "role": Role.CHIEF_WARDEN,
                "escalation_level": 3,
                "is_staff": True,
            },
        )
        chief_warden.set_password("pass1234")
        chief_warden.theme = Theme.SYSTEM
        chief_warden.save()

        # Wardens
        warden_a, _ = User.objects.get_or_create(
            login_id="warden_bha",
            defaults={
                "full_name": "Dr. Ramesh Verma",
                "role": Role.WARDEN,
                "escalation_level": 2,
                "hostel": hostel_a,
                "is_staff": True,
            },
        )
        warden_a.set_password("pass1234")
        warden_a.theme = Theme.LIGHT
        warden_a.hostel = hostel_a
        warden_a.save()

        warden_b, _ = User.objects.get_or_create(
            login_id="warden_ghb",
            defaults={
                "full_name": "Dr. Sunita Patel",
                "role": Role.WARDEN,
                "escalation_level": 2,
                "hostel": hostel_b,
                "is_staff": True,
            },
        )
        warden_b.set_password("pass1234")
        warden_b.theme = Theme.DARK
        warden_b.hostel = hostel_b
        warden_b.save()

        # Caretakers
        caretakers_a = []
        for cid, name in [
            ("caretaker_bha1", "Mukesh Kumar"),
            ("caretaker_bha2", "Rajesh Singh"),
        ]:
            u, _ = User.objects.get_or_create(
                login_id=cid,
                defaults={
                    "full_name": name,
                    "role": Role.CARETAKER,
                    "escalation_level": 1,
                    "hostel": hostel_a,
                    "is_staff": True,
                },
            )
            u.set_password("pass1234")
            u.theme = Theme.DARK if cid == "caretaker_bha1" else Theme.SYSTEM
            u.hostel = hostel_a
            u.save()
            caretakers_a.append(u)

        caretakers_b = []
        for cid, name in [
            ("caretaker_ghb1", "Anita Devi"),
            ("caretaker_ghb2", "Pooja Sharma"),
        ]:
            u, _ = User.objects.get_or_create(
                login_id=cid,
                defaults={
                    "full_name": name,
                    "role": Role.CARETAKER,
                    "escalation_level": 1,
                    "hostel": hostel_b,
                    "is_staff": True,
                },
            )
            u.set_password("pass1234")
            u.theme = Theme.LIGHT if cid == "caretaker_ghb1" else Theme.SYSTEM
            u.hostel = hostel_b
            u.save()
            caretakers_b.append(u)

        # Set Level 1 responsible staff for all 12 hostels + wardens
        for h in all_hostels:
            ct_login = f"caretaker_{h.code.lower().replace('-', '')}"
            ct, _ = User.objects.get_or_create(
                login_id=ct_login,
                defaults={
                    "full_name": f"Caretaker ({h.code})",
                    "role": Role.CARETAKER,
                    "escalation_level": 1,
                    "hostel": h,
                    "is_staff": True,
                },
            )
            ct.set_password("pass1234")
            ct.hostel = h
            ct.save()
            h.responsible_staff = ct
            h.save(update_fields=["responsible_staff"])

            wd_login = f"warden_{h.code.lower().replace('-', '')}"
            wd, _ = User.objects.get_or_create(
                login_id=wd_login,
                defaults={
                    "full_name": f"Warden ({h.code})",
                    "role": Role.WARDEN,
                    "escalation_level": 2,
                    "hostel": h,
                    "is_staff": True,
                },
            )
            wd.set_password("pass1234")
            wd.hostel = h
            wd.save()

        # Backward compatibility for demo accounts on login screen
        hostel_a.responsible_staff = caretakers_a[0]
        hostel_a.save()
        hostel_b.responsible_staff = caretakers_b[0]
        hostel_b.save()

        # 22 Hostelers (14 in Hostel A, 8 in Hostel B)
        # Note: student_14 and student_22 are deliberately unassigned to demo onboarding gate
        # student_12 is pending verification; student_13 is rejected to test verification queues
        now = timezone.now()
        theme_cycle = [Theme.SYSTEM, Theme.DARK, Theme.LIGHT]
        students_a = []
        for i in range(1, 15):
            lid = f"student_{i:02d}"
            assigned_room = rooms_a[(i - 1) % len(rooms_a)] if i < 14 else None
            is_ver = (i < 12)
            rej_rsn = "Discrepancy in room allocation" if i == 13 else ""
            u, _ = User.objects.get_or_create(
                login_id=lid,
                defaults={
                    "full_name": f"Hosteler {i} (Boys)",
                    "role": Role.HOSTELER,
                    "hostel": hostel_a if i < 14 else None,
                    "room": assigned_room,
                    "residence_set_at": now if assigned_room else None,
                    "theme": theme_cycle[i % 3],
                    "is_verified": is_ver,
                    "rejected_reason": rej_rsn,
                },
            )
            u.set_password("pass1234")
            if assigned_room and not u.room:
                u.hostel = hostel_a
                u.room = assigned_room
                u.residence_set_at = now
            u.theme = theme_cycle[i % 3]
            u.is_verified = is_ver
            u.rejected_reason = rej_rsn
            u.save()
            if assigned_room:
                ResidenceHistory.objects.get_or_create(
                    user=u,
                    hostel=hostel_a,
                    room=assigned_room,
                    defaults={"changed_by": admin_user},
                )
            students_a.append(u)

        students_b = []
        for i in range(15, 23):
            lid = f"student_{i:02d}"
            assigned_room = rooms_b[(i - 15) % len(rooms_b)] if i < 22 else None
            u, _ = User.objects.get_or_create(
                login_id=lid,
                defaults={
                    "full_name": f"Hosteler {i} (Girls)",
                    "role": Role.HOSTELER,
                    "hostel": hostel_b if i < 22 else None,
                    "room": assigned_room,
                    "residence_set_at": now if assigned_room else None,
                    "theme": theme_cycle[i % 3],
                },
            )
            u.set_password("pass1234")
            if assigned_room and not u.room:
                u.hostel = hostel_b
                u.room = assigned_room
                u.residence_set_at = now
            u.theme = theme_cycle[i % 3]
            u.save()
            if assigned_room:
                ResidenceHistory.objects.get_or_create(
                    user=u,
                    hostel=hostel_b,
                    room=assigned_room,
                    defaults={"changed_by": admin_user},
                )
            students_b.append(u)

        self.stdout.write(
            "Users seeded (1 Admin, 1 Chief Warden, 2 Wardens, 4 Caretakers, 22 Students with 2 pending onboarding)."
        )

        # 4. Routing Rules
        categories = list(Category.objects.all())
        if not categories:
            # Fallback if categories not yet seeded
            for cname in [
                "Electrical",
                "Plumbing",
                "Carpentry",
                "Wi-Fi & LAN",
                "Civil",
                "Cleaning",
            ]:
                cat, _ = Category.objects.get_or_create(name=cname)
                categories.append(cat)

        for cat in categories:
            RoutingRule.objects.get_or_create(
                hostel=hostel_a,
                category=cat,
                defaults={"assignee": caretakers_a[0], "level": 1},
            )
            RoutingRule.objects.get_or_create(
                hostel=hostel_b,
                category=cat,
                defaults={"assignee": caretakers_b[0], "level": 1},
            )

        # 5. Seed 60 Realistic Tickets
        ticket_samples = [
            (
                "Ceiling fan regulator not working",
                "Fan only runs at full speed #5 and switch sparks slightly.",
                "Electrical",
                Priority.HIGH,
            ),
            (
                "Washroom sink tap dripping continuously",
                "Tap in room bathroom drips approximately 1 drop per second.",
                "Plumbing",
                Priority.MEDIUM,
            ),
            (
                "Wi-Fi router in 2nd floor corridor dropping connection",
                "Cannot connect to eduroam / hostel Wi-Fi during evening hours.",
                "Wi-Fi & LAN",
                Priority.HIGH,
            ),
            (
                "Bed frame bolt loose causing creaking sound",
                "Center leg support is unsteady when sleeping.",
                "Carpentry",
                Priority.LOW,
            ),
            (
                "Water cooler on 1st floor not chilling water",
                "Cooler running but water temperature remains lukewarm.",
                "Electrical",
                Priority.MEDIUM,
            ),
            (
                "Study table lamp socket loose",
                "Plug socket is loose and sparks when charger is plugged in.",
                "Electrical",
                Priority.HIGH,
            ),
            (
                "Bathroom door latch jammed from inside",
                "Latch gets stuck and difficult to slide open.",
                "Carpentry",
                Priority.URGENT,
            ),
            (
                "Geyser not heating water in Wing B",
                "Takes 45 minutes and still only lukewarm water comes out.",
                "Electrical",
                Priority.MEDIUM,
            ),
            (
                "Room window glass cracked after heavy storm",
                "Outer glass pane has a spider crack from high winds.",
                "Civil",
                Priority.MEDIUM,
            ),
            (
                "Drain blockage in common bathroom",
                "Water stagnates during showers and drains very slowly.",
                "Plumbing",
                Priority.HIGH,
            ),
            (
                "Corridor tube light flickering constantly",
                "Outside room 103, causing disturbance at night.",
                "Electrical",
                Priority.LOW,
            ),
            (
                "Cupboard handle broken",
                "Left cupboard handle sheared off.",
                "Carpentry",
                Priority.LOW,
            ),
            (
                "LAN port wall plate damaged",
                "RJ-45 connector pin broken inside wall socket.",
                "Wi-Fi & LAN",
                Priority.MEDIUM,
            ),
            (
                "Exhaust fan making high pitched squeal",
                "Bathroom exhaust motor bearing seems worn out.",
                "Electrical",
                Priority.LOW,
            ),
            (
                "Main door lock cylinder stiff",
                "Key requires excessive force to turn.",
                "Carpentry",
                Priority.MEDIUM,
            ),
            (
                "Shower head spray blocked by lime scale",
                "Uneven pressure and spraying sideways.",
                "Plumbing",
                Priority.LOW,
            ),
            (
                "Ceiling seepage spot near balcony door",
                "Damp patch appearing during monsoon.",
                "Civil",
                Priority.HIGH,
            ),
            (
                "Switchboard cover plate cracked",
                "Needs replacement for safety.",
                "Electrical",
                Priority.MEDIUM,
            ),
            (
                "Flush tank valve leaking into toilet bowl",
                "Continuous trickling sound waste of water.",
                "Plumbing",
                Priority.MEDIUM,
            ),
            (
                "Curtain rod fell off wall bracket",
                "Screws pulled out of drywall.",
                "Carpentry",
                Priority.LOW,
            ),
        ]

        now = timezone.now()
        year = now.year

        # Target counts for statuses
        statuses_dist = (
            [Status.OPEN] * 10
            + [Status.ASSIGNED] * 12
            + [Status.IN_PROGRESS] * 14
            + [Status.ON_HOLD] * 4
            + [Status.RESOLVED] * 12
            + [Status.CLOSED] * 8
        )

        # Ensure ticket list contains 60 tickets
        while len(ticket_samples) < 60:
            base_title, base_desc, base_cat, base_prio = random.choice(ticket_samples[:20])
            ticket_samples.append(
                (f"{base_title} (Sector {len(ticket_samples)+1})", base_desc, base_cat, base_prio)
            )

        random.shuffle(statuses_dist)

        created_count = 0
        for i in range(1, 61):
            ticket_no = f"HTL-{year}-{i:05d}"
            title, desc, cat_name, prio = ticket_samples[i - 1]
            status = statuses_dist[i - 1]

            # Alternate between Hostel A and B
            is_hostel_a = i % 2 == 1
            hostel = hostel_a if is_hostel_a else hostel_b
            students = students_a if is_hostel_a else students_b
            caretakers = caretakers_a if is_hostel_a else caretakers_b
            warden = warden_a if is_hostel_a else warden_b

            reporter = random.choice(students)
            category = next((c for c in categories if c.name == cat_name), categories[0])

            # Pick level and assignee based on status & simulated escalation
            if i in [1, 5, 12]:  # Escalated to L4 Admin
                current_level = 4
                assignee = admin_user
            elif i in [2, 8, 17, 24]:  # Escalated to L3 Chief Warden
                current_level = 3
                assignee = chief_warden
            elif i in [3, 9, 15, 21, 33]:  # Escalated to L2 Warden
                current_level = 2
                assignee = warden
            else:
                current_level = 1
                assignee = random.choice(caretakers)

            if status == Status.OPEN:
                assignee = None

            # Created timestamp distributed over last 30 days
            created_days_ago = random.randint(1, 28)
            created_at = now - timedelta(days=created_days_ago, hours=random.randint(1, 12))

            # SLA due_at: 24h to 72h from created_at
            due_at = created_at + timedelta(hours=random.choice([24, 48, 72]))

            # Is overdue check (5 tickets simulated overdue)
            is_overdue = False
            if i in [1, 2, 5, 17, 30] and status not in [Status.RESOLVED, Status.CLOSED]:
                due_at = now - timedelta(hours=random.randint(4, 48))
                is_overdue = True

            resolved_at = None
            if status in [Status.RESOLVED, Status.CLOSED]:
                resolved_at = created_at + timedelta(hours=random.randint(6, 36))
                if resolved_at > now:
                    resolved_at = now - timedelta(hours=2)

            reporter_room = reporter.room if (reporter and reporter.room) else (rooms_a[0] if is_hostel_a else rooms_b[0])
            is_outside = bool(reporter and reporter.hostel_id and reporter.hostel_id != hostel.id)

            ticket, created = Ticket.objects.get_or_create(
                ticket_no=ticket_no,
                defaults={
                    "title": title,
                    "description": desc,
                    "category": category,
                    "priority": prio,
                    "status": status,
                    "hostel": hostel,
                    "room": reporter_room,
                    "outside_own_hostel": is_outside,
                    "reporter": reporter,
                    "assigned_to": assignee,
                    "current_level": current_level,
                    "due_at": due_at,
                    "is_overdue": is_overdue,
                    "resolved_at": resolved_at,
                },
            )

            if created:
                # Override auto_now_add with simulated created_at
                Ticket.objects.filter(pk=ticket.pk).update(
                    created_at=created_at, updated_at=resolved_at or now
                )

                # Add initial activity log
                TicketActivity.objects.create(
                    ticket=ticket,
                    actor=reporter,
                    action=ActivityAction.CREATED,
                    to_value=Status.OPEN,
                    note="Ticket submitted by hosteler.",
                )

                if assignee:
                    TicketActivity.objects.create(
                        ticket=ticket,
                        actor=assignee,
                        action=ActivityAction.ASSIGNED,
                        to_value=assignee.login_id,
                        note=f"Assigned at Level {current_level}.",
                    )

                # Add comments
                if status in [Status.IN_PROGRESS, Status.RESOLVED, Status.CLOSED]:
                    TicketComment.objects.create(
                        ticket=ticket,
                        author=assignee or caretakers[0],
                        body="Inspected the site. Spare parts have been requisitioned from the central store.",
                        is_internal=False,
                    )
                    # Internal staff note
                    TicketComment.objects.create(
                        ticket=ticket,
                        author=assignee or caretakers[0],
                        body="Vendor quoted ₹350 for replacement component. Bill submitted to accounts.",
                        is_internal=True,
                    )

                if status == Status.RESOLVED:
                    TicketComment.objects.create(
                        ticket=ticket,
                        author=assignee or caretakers[0],
                        body="Component replaced and tested. Everything is functioning normally.",
                        is_internal=False,
                    )

                if status == Status.CLOSED:
                    TicketComment.objects.create(
                        ticket=ticket,
                        author=reporter,
                        body="Verified, the issue has been resolved. Thank you!",
                        is_internal=False,
                    )

                created_count += 1

        # ==============================================================================
        # 6. Seed 5 Announcements Across Severities and Statuses
        # ==============================================================================
        self.stdout.write("Seeding 5 announcements across severities and statuses...")
        announcements_data = [
            {
                "title": "Urgent: Water Supply Shutdown for Overhead Tank Cleaning",
                "body": "Municipal cleaning crew will be sanitizing all rooftop storage tanks on Saturday between 09:00 and 15:00. Please store necessary water beforehand.",
                "kind": AnnouncementKind.MAINTENANCE,
                "severity": AnnouncementSeverity.URGENT,
                "status": AnnouncementStatus.PUBLISHED,
                "is_pinned": True,
                "all_hostels": True,
                "published_at": now - timedelta(hours=4),
            },
            {
                "title": "Mess Rebate and Semester Break Vacation Guidelines",
                "body": "Students leaving campus during semester break must submit online mess rebate forms at least 48 hours in advance to avoid boarding charges.",
                "kind": AnnouncementKind.POLICY,
                "severity": AnnouncementSeverity.IMPORTANT,
                "status": AnnouncementStatus.PUBLISHED,
                "is_pinned": True,
                "all_hostels": True,
                "published_at": now - timedelta(days=2),
            },
            {
                "title": "Central Reading Room 24/7 Schedule During Exam Month",
                "body": "The air-conditioned reading room in Boys Hostel A and Girls Hostel B will remain open around the clock with security coverage throughout mid-semesters.",
                "kind": AnnouncementKind.NOTICE,
                "severity": AnnouncementSeverity.INFO,
                "status": AnnouncementStatus.PUBLISHED,
                "is_pinned": False,
                "all_hostels": True,
                "published_at": now - timedelta(days=5),
            },
            {
                "title": "Inter-Hostel Badminton & Table Tennis Tournament Registration",
                "body": "Registration is now open for the annual hostel sports meet. Teams can submit rosters to the sports secretary before next Friday.",
                "kind": AnnouncementKind.EVENT,
                "severity": AnnouncementSeverity.INFO,
                "status": AnnouncementStatus.SCHEDULED,
                "is_pinned": False,
                "all_hostels": True,
                "publish_at": now + timedelta(days=2),
            },
            {
                "title": "Draft Protocol: Annual Fire Safety & Evacuation Drill",
                "body": "Detailed guidelines regarding assembly points, warden responsibilities, and emergency sirens during the upcoming mock fire drill.",
                "kind": AnnouncementKind.NOTICE,
                "severity": AnnouncementSeverity.IMPORTANT,
                "status": AnnouncementStatus.DRAFT,
                "is_pinned": False,
                "all_hostels": True,
            },
        ]

        for a_data in announcements_data:
            ann, created = Announcement.objects.get_or_create(
                title=a_data["title"],
                defaults={
                    "body": a_data["body"],
                    "kind": a_data["kind"],
                    "severity": a_data["severity"],
                    "status": a_data["status"],
                    "is_pinned": a_data.get("is_pinned", False),
                    "author": warden_a,
                    "all_hostels": a_data.get("all_hostels", True),
                    "published_at": a_data.get("published_at"),
                    "publish_at": a_data.get("publish_at"),
                },
            )
            if a_data["status"] == AnnouncementStatus.PUBLISHED:
                # Mark as read by a few students to show realistic read rates
                for s in students_a[:6]:
                    AnnouncementRead.objects.get_or_create(announcement=ann, user=s)

        # ==============================================================================
        # 9. Seed Soft-Deleted Tickets for Trash Management Demo
        # ==============================================================================
        self.stdout.write("Seeding soft-deleted tickets for trash management demo...")
        del_samples = [
            (
                "Duplicate: Ceiling fan speed regulator broken",
                "Accidentally created duplicate ticket for ceiling fan",
                students_a[0],
                hostel_a,
                students_a[0],
                "Created duplicate ticket by mistake",
            ),
            (
                "Spam test ticket - please delete",
                "Checking if ticket notification works",
                students_a[1],
                hostel_a,
                warden_a,
                "Spam or test ticket submitted by student",
            ),
            (
                "Obsolete item: Old cafeteria feedback",
                "Cafeteria menu suggestion from past semester",
                students_b[0],
                hostel_b,
                admin_user,
                "Raised by mistake in maintenance category",
            ),
        ]

        elec_cat = Category.objects.filter(name="Electrical").first() or categories[0]
        for idx, (title, desc, rep, hst, actor, rsn) in enumerate(del_samples, start=1):
            t_no = f"HTL-{now.year}-{80+idx:05d}"
            rep_room = rep.room if (rep and rep.room) else (rooms_a[0] if hst == hostel_a else rooms_b[0])
            del_ticket, created = Ticket.all_objects.get_or_create(
                ticket_no=t_no,
                defaults={
                    "title": title,
                    "description": desc,
                    "category": elec_cat,
                    "hostel": hst,
                    "room": rep_room,
                    "reporter": rep,
                    "priority": Priority.LOW,
                    "status": Status.OPEN,
                    "is_deleted": False,
                },
            )
            if created or not del_ticket.is_deleted:
                soft_delete(del_ticket, actor=actor, reason=rsn)

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded demo dataset with {created_count} realistic tickets, 3 soft-deleted trash tickets, and 5 announcements!"
            )
        )
