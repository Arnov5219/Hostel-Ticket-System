import random
from datetime import timedelta

from django.core.files.base import ContentFile
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
from apps.notifications.models import Notification, NotificationVerb
from apps.tickets.models import (
    ActivityAction,
    Category,
    Priority,
    RoutingRule,
    Status,
    Ticket,
    TicketActivity,
    TicketAttachment,
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
        call_command("seed_demo_accounts")

        # Admin
        admin_user, _ = User.objects.get_or_create(
            login_id="ADMIN",
            defaults={
                "full_name": "System Administrator",
                "role": Role.ADMIN,
                "escalation_level": None,
                "is_staff": True,
                "is_superuser": True,
                "is_demo": True,
            },
        )
        admin_user.set_password("me1234")
        admin_user.theme = Theme.DARK
        admin_user.is_demo = True
        admin_user.escalation_level = None
        admin_user.save()

        # Dean (L4)
        dean_user, _ = User.objects.get_or_create(
            login_id="DEAN",
            defaults={
                "full_name": "Dr. K. V. Dean",
                "role": Role.DEAN,
                "escalation_level": 4,
                "is_staff": True,
                "is_demo": True,
            },
        )
        dean_user.set_password("me1234")
        dean_user.theme = Theme.SYSTEM
        dean_user.is_demo = True
        dean_user.save()

        # Chief Warden (L3)
        chief_warden, _ = User.objects.get_or_create(
            login_id="CHIEF_WARDEN",
            defaults={
                "full_name": "Prof. S. K. Sharma",
                "role": Role.CHIEF_WARDEN,
                "escalation_level": 3,
                "is_staff": True,
                "is_demo": True,
            },
        )
        chief_warden.set_password("me1234")
        chief_warden.theme = Theme.SYSTEM
        chief_warden.is_demo = True
        chief_warden.save()

        # Wardens
        warden_a, _ = User.objects.get_or_create(
            login_id="WARDEN_BHA",
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
            login_id="WARDEN_GHB",
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
                login_id=cid.upper(),
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
                login_id=cid.upper(),
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
            ct_login = f"caretaker_{h.code.lower().replace('-', '')}".upper()
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

            wd_login = f"warden_{h.code.lower().replace('-', '')}".upper()
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
            lid = f"student_{i:02d}".upper()
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
            lid = f"student_{i:02d}".upper()
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
                    )
                    # Internal staff note
                    TicketComment.objects.create(
                        ticket=ticket,
                        author=assignee or caretakers[0],
                        body="Vendor quoted ₹350 for replacement component. Bill submitted to accounts.",
                    )

                if status == Status.RESOLVED:
                    TicketComment.objects.create(
                        ticket=ticket,
                        author=assignee or caretakers[0],
                        body="Component replaced and tested. Everything is functioning normally.",
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

        # ==============================================================================
        # 10. Guarantee Section 6 Coverage for Standardized Demo Roles (L0..L5)
        # ==============================================================================
        self.stdout.write("Ensuring Section 6 coverage for L0..L5 demo accounts and multi-hostel dashboard...")
        l0 = User.objects.filter(login_id="L0").first()
        l1 = User.objects.filter(login_id="L1").first()
        l2 = User.objects.filter(login_id="L2").first()
        l3 = User.objects.filter(login_id="L3").first()
        l4 = User.objects.filter(login_id="L4").first()

        hostel_bh1 = Hostel.objects.filter(code="BH-1").first() or all_hostels[0]
        room_bh1 = hostel_bh1.rooms.filter(is_active=True).first()

        png_sample = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06"
            b"\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
            b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )

        cat_elec = Category.objects.filter(name="Electrical").first() or categories[0]
        cat_plumb = Category.objects.filter(name="Plumbing").first() or categories[0]
        cat_carp = Category.objects.filter(name="Carpentry").first() or categories[0]
        cat_wifi = Category.objects.filter(name="Wi-Fi & LAN").first() or categories[0]
        cat_civil = Category.objects.filter(name="Civil").first() or categories[0]

        if l0 and l1:
            l0_tickets_def = [
                {
                    "no": f"HTL-{now.year}-00101",
                    "title": "Ceiling fan speed regulator broken",
                    "desc": "Regulator knob rotates freely without changing speed; fan stuck on high.",
                    "cat": cat_elec,
                    "prio": Priority.HIGH,
                    "status": Status.OPEN,
                    "assignee": None,
                    "level": 1,
                    "has_photo": True,
                    "overdue": False,
                },
                {
                    "no": f"HTL-{now.year}-00102",
                    "title": "Washroom tap dripping continuously",
                    "desc": "Washbasin faucet dripping at steady rate and wasting water.",
                    "cat": cat_plumb,
                    "prio": Priority.MEDIUM,
                    "status": Status.ASSIGNED,
                    "assignee": l1,
                    "level": 1,
                    "has_photo": False,
                    "overdue": False,
                },
                {
                    "no": f"HTL-{now.year}-00103",
                    "title": "Bathroom light socket sparking",
                    "desc": "Noticeable spark when switching on the bathroom mirror light.",
                    "cat": cat_elec,
                    "prio": Priority.HIGH,
                    "status": Status.IN_PROGRESS,
                    "assignee": l1,
                    "level": 1,
                    "has_photo": True,
                    "overdue": False,
                },
                {
                    "no": f"HTL-{now.year}-00104",
                    "title": "Study table drawer slider stuck",
                    "desc": "Right-hand drawer runner derailed and jammed shut.",
                    "cat": cat_carp,
                    "prio": Priority.LOW,
                    "status": Status.ON_HOLD,
                    "assignee": l1,
                    "level": 1,
                    "has_photo": False,
                    "overdue": False,
                    "hold_note": "Awaiting replacement slide brackets from vendor store.",
                },
                {
                    "no": f"HTL-{now.year}-00105",
                    "title": "Corridor Wi-Fi access point reboot required",
                    "desc": "Intermittent disconnects on 1st floor wing A.",
                    "cat": cat_wifi,
                    "prio": Priority.MEDIUM,
                    "status": Status.RESOLVED,
                    "assignee": l1,
                    "level": 1,
                    "has_photo": False,
                    "overdue": False,
                    "resolved_hours_ago": 2,
                },
                {
                    "no": f"HTL-{now.year}-00106",
                    "title": "Door latch alignment and strike plate adjustment",
                    "desc": "Door bolt did not catch frame without slamming.",
                    "cat": cat_carp,
                    "prio": Priority.LOW,
                    "status": Status.CLOSED,
                    "assignee": l1,
                    "level": 1,
                    "has_photo": False,
                    "overdue": False,
                    "resolved_hours_ago": 120,
                    "closed_hours_ago": 96,
                    "rating": 5,
                },
                {
                    "no": f"HTL-{now.year}-00107",
                    "title": "Water seepage on north wall near balcony",
                    "desc": "Plaster peeling and damp spot expanding along balcony beam.",
                    "cat": cat_civil,
                    "prio": Priority.HIGH,
                    "status": Status.IN_PROGRESS,
                    "assignee": l1,
                    "level": 1,
                    "has_photo": False,
                    "overdue": True,
                },
                {
                    "no": f"HTL-{now.year}-00108",
                    "title": "Emergency water pipe rupture in common washroom",
                    "desc": "Main supply pipe leaking heavily near riser valve.",
                    "cat": cat_plumb,
                    "prio": Priority.URGENT,
                    "status": Status.IN_PROGRESS,
                    "assignee": l2 or l1,
                    "level": 2,
                    "has_photo": False,
                    "overdue": False,
                },
            ]

            for t_spec in l0_tickets_def:
                t_obj, created = Ticket.objects.get_or_create(
                    ticket_no=t_spec["no"],
                    defaults={
                        "title": t_spec["title"],
                        "description": t_spec["desc"],
                        "category": t_spec["cat"],
                        "priority": t_spec["prio"],
                        "status": t_spec["status"],
                        "hostel": hostel_bh1,
                        "room": room_bh1,
                        "reporter": l0,
                        "assigned_to": t_spec["assignee"],
                        "current_level": t_spec["level"],
                        "due_at": now - timedelta(days=2) if t_spec.get("overdue") else now + timedelta(days=2),
                        "is_overdue": t_spec.get("overdue", False),
                        "rating": t_spec.get("rating"),
                        "resolved_at": now - timedelta(hours=t_spec["resolved_hours_ago"]) if "resolved_hours_ago" in t_spec else None,
                        "closed_at": now - timedelta(hours=t_spec["closed_hours_ago"]) if "closed_hours_ago" in t_spec else None,
                    },
                )
                if not created:
                    t_obj.status = t_spec["status"]
                    t_obj.assigned_to = t_spec["assignee"]
                    t_obj.current_level = t_spec["level"]
                    t_obj.is_overdue = t_spec.get("overdue", False)
                    if t_spec.get("rating"):
                        t_obj.rating = t_spec["rating"]
                    if "resolved_hours_ago" in t_spec:
                        t_obj.resolved_at = now - timedelta(hours=t_spec["resolved_hours_ago"])
                    if "closed_hours_ago" in t_spec:
                        t_obj.closed_at = now - timedelta(hours=t_spec["closed_hours_ago"])
                    t_obj.save()

                if t_spec.get("has_photo") and not t_obj.attachments.exists():
                    TicketAttachment.objects.create(
                        ticket=t_obj,
                        uploaded_by=l0,
                        file=ContentFile(png_sample, name=f"photo_{t_obj.ticket_no}.png"),
                    )

                if t_spec.get("hold_note"):
                    TicketComment.objects.get_or_create(
                        ticket=t_obj,
                        author=l1,
                        body=t_spec["hold_note"],
                    )

            # L1 Caretaker assigned tickets across all 5 Kanban statuses
            l1_extra_statuses = [
                (f"HTL-{now.year}-00111", "Geyser element replacement", cat_elec, Priority.MEDIUM, Status.ASSIGNED),
                (f"HTL-{now.year}-00112", "Broken window latch room 204", cat_carp, Priority.LOW, Status.IN_PROGRESS),
                (f"HTL-{now.year}-00113", "Corridor tile regrouting", cat_civil, Priority.LOW, Status.ON_HOLD),
                (f"HTL-{now.year}-00114", "Shower head descaling", cat_plumb, Priority.LOW, Status.RESOLVED),
            ]
            for ext_no, ext_title, ext_cat, ext_prio, ext_st in l1_extra_statuses:
                ext_t, ext_created = Ticket.objects.get_or_create(
                    ticket_no=ext_no,
                    defaults={
                        "title": ext_title,
                        "description": f"Maintenance issue in {hostel_bh1.name}.",
                        "category": ext_cat,
                        "priority": ext_prio,
                        "status": ext_st,
                        "hostel": hostel_bh1,
                        "room": room_bh1,
                        "reporter": students_a[1],
                        "assigned_to": l1,
                        "current_level": 1,
                        "due_at": now + timedelta(hours=24),
                        "resolved_at": now - timedelta(hours=4) if ext_st == Status.RESOLVED else None,
                    },
                )
                if not ext_created:
                    ext_t.status = ext_st
                    ext_t.assigned_to = l1
                    ext_t.save()

            # Escalated queues for L2, L3, and L4 (with L4 Critical Overdue)
            if l4:
                crit_t, _ = Ticket.objects.get_or_create(
                    ticket_no=f"HTL-{now.year}-00120",
                    defaults={
                        "title": "Critical: Campus Central Water Filtration Pump Failure",
                        "description": "Primary motor seized. Standby generator transfer switch failing. Affecting multiple residential blocks.",
                        "category": cat_civil,
                        "priority": Priority.URGENT,
                        "status": Status.IN_PROGRESS,
                        "hostel": hostel_bh1,
                        "reporter": students_a[2],
                        "assigned_to": l4,
                        "current_level": 4,
                        "due_at": now - timedelta(days=3),
                        "is_overdue": True,
                    },
                )
                crit_t.current_level = 4
                crit_t.assigned_to = l4
                crit_t.is_overdue = True
                crit_t.priority = Priority.URGENT
                crit_t.save()

            if l3:
                l3_t, _ = Ticket.objects.get_or_create(
                    ticket_no=f"HTL-{now.year}-00121",
                    defaults={
                        "title": "Solar Water Heater Controller Malfunction",
                        "description": "High temperature cutoff tripping repeatedly across north wing roof.",
                        "category": cat_elec,
                        "priority": Priority.HIGH,
                        "status": Status.ASSIGNED,
                        "hostel": hostel_bh1,
                        "reporter": students_a[3],
                        "assigned_to": l3,
                        "current_level": 3,
                        "due_at": now + timedelta(hours=12),
                    },
                )
                l3_t.current_level = 3
                l3_t.assigned_to = l3
                l3_t.save()

            # Varied SLA and at least two alert hostels across all 12 hostels
            for idx, h in enumerate(all_hostels):
                t_hostel_no = f"HTL-{now.year}-002{idx:02d}"
                h_overdue = (idx in [2, 5])  # BH-3 and GH-2 have alert overdue tickets
                Ticket.objects.get_or_create(
                    ticket_no=t_hostel_no,
                    defaults={
                        "title": f"Periodic inspection & maintenance in {h.name}",
                        "description": f"Standard maintenance checkup for {h.code} block.",
                        "category": cat_elec,
                        "priority": Priority.HIGH if h_overdue else Priority.MEDIUM,
                        "status": Status.IN_PROGRESS,
                        "hostel": h,
                        "reporter": students_a[0],
                        "assigned_to": h.responsible_staff or l1,
                        "current_level": 1,
                        "due_at": now - timedelta(days=2) if h_overdue else now + timedelta(days=2),
                        "is_overdue": h_overdue,
                    },
                )

            # Notifications for L0: at least 6 mixed types, 2 unread
            Notification.objects.filter(recipient=l0).delete()
            notif_specs = [
                (NotificationVerb.CREATED, "Ticket HTL-...-00101 submitted successfully.", True),
                (NotificationVerb.ASSIGNED, "Ticket HTL-...-00102 assigned to Demo Caretaker.", True),
                (NotificationVerb.STATUS_CHANGED, "Ticket HTL-...-00103 moved to In Progress.", True),
                (NotificationVerb.COMMENTED, "Demo Caretaker added an update: 'Inspected the site.'", True),
                (NotificationVerb.RESOLVED, "Ticket HTL-...-00105 marked as Resolved. Please confirm closure.", False),
                (NotificationVerb.ANNOUNCEMENT, "Urgent Notice: Overhead Water Tank Cleaning scheduled.", False),
            ]
            for verb, msg, is_rd in notif_specs:
                Notification.objects.create(
                    recipient=l0,
                    verb=verb,
                    message=msg,
                    is_read=is_rd,
                )

            # Announcements: ensure one urgent unread for L0, one expired
            # Expired announcement
            Announcement.objects.get_or_create(
                title="Library Extended Hours for End-Semester Exams (Concluded)",
                defaults={
                    "body": "Special exam hours have concluded. Standard reading room schedule resumed.",
                    "kind": AnnouncementKind.NOTICE,
                    "severity": AnnouncementSeverity.INFO,
                    "status": AnnouncementStatus.PUBLISHED,
                    "is_pinned": False,
                    "author": l2 or warden_a,
                    "all_hostels": True,
                    "published_at": now - timedelta(days=14),
                    "expires_at": now - timedelta(days=2),
                },
            )
            # Ensure L0 has NOT read the urgent announcement
            urgent_ann = Announcement.objects.filter(severity=AnnouncementSeverity.URGENT).first()
            if urgent_ann:
                AnnouncementRead.objects.filter(announcement=urgent_ann, user=l0).delete()

        self.stdout.write(
            self.style.SUCCESS(
                "Successfully seeded demo dataset with realistic tickets, Section 6 coverage for L0..L5, and announcements!"
            )
        )
