import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.hostels.models import Block, GenderType, Hostel, Room
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


class Command(BaseCommand):
    help = "Seeds comprehensive demo data: hostels, blocks, rooms, users, routing rules, and 60 realistic tickets"

    def handle(self, *args, **options):
        self.stdout.write("Starting comprehensive demo data seeding...")

        # 1. Seed Hostels
        hostel_a, _ = Hostel.objects.get_or_create(
            code="BH-A",
            defaults={
                "name": "Boys Hostel A",
                "gender_type": GenderType.BOYS,
                "address": "North Campus, Hall of Residence 1",
            },
        )
        hostel_b, _ = Hostel.objects.get_or_create(
            code="GH-B",
            defaults={
                "name": "Girls Hostel B",
                "gender_type": GenderType.GIRLS,
                "address": "South Campus, Hall of Residence 2",
            },
        )

        # 2. Seed Blocks & Rooms (2 blocks each, 10 rooms each = 20 rooms per hostel)
        rooms_a = []
        rooms_b = []

        for hostel, r_list, blk_names in [
            (hostel_a, rooms_a, ["Block 1", "Block 2"]),
            (hostel_b, rooms_b, ["Block A", "Block B"]),
        ]:
            for b_idx, b_name in enumerate(blk_names, start=1):
                block, _ = Block.objects.get_or_create(hostel=hostel, name=b_name)
                for floor in [1, 2]:
                    for r_num in range(1, 6):
                        room_no = f"{b_idx}{floor}0{r_num}"
                        room, _ = Room.objects.get_or_create(
                            block=block,
                            room_number=room_no,
                            defaults={"floor": floor, "capacity": 2},
                        )
                        r_list.append(room)

        self.stdout.write(f"Created {len(rooms_a)} rooms in BH-A and {len(rooms_b)} rooms in GH-B.")

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
            u.save()
            caretakers_b.append(u)

        # 15 Hostelers
        students_a = []
        for i in range(1, 9):
            lid = f"student_{i:02d}"
            room = rooms_a[i - 1]
            u, _ = User.objects.get_or_create(
                login_id=lid,
                defaults={
                    "full_name": f"Hosteler {i} (Boys)",
                    "role": Role.HOSTELER,
                    "hostel": hostel_a,
                    "room": room,
                },
            )
            u.set_password("pass1234")
            u.save()
            students_a.append(u)

        students_b = []
        for i in range(9, 16):
            lid = f"student_{i:02d}"
            room = rooms_b[i - 9]
            u, _ = User.objects.get_or_create(
                login_id=lid,
                defaults={
                    "full_name": f"Hosteler {i} (Girls)",
                    "role": Role.HOSTELER,
                    "hostel": hostel_b,
                    "room": room,
                },
            )
            u.set_password("pass1234")
            u.save()
            students_b.append(u)

        self.stdout.write(
            "Users seeded (1 Admin, 1 Chief Warden, 2 Wardens, 4 Caretakers, 15 Students)."
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

            ticket, created = Ticket.objects.get_or_create(
                ticket_no=ticket_no,
                defaults={
                    "title": title,
                    "description": desc,
                    "category": category,
                    "priority": prio,
                    "status": status,
                    "hostel": hostel,
                    "room": reporter.room,
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

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded demo dataset with {created_count} realistic tickets, comments, and activities!"
            )
        )
