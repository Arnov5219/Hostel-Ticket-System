from dataclasses import dataclass

from django.urls import reverse

from apps.accounts.models import Role
from apps.core.permissions import Capability


@dataclass
class NavItem:
    key: str
    label: str
    icon: str
    url_name: str
    section: str
    badge_key: str | None = None
    is_action: bool = False

    @property
    def url(self) -> str:
        try:
            return reverse(self.url_name)
        except Exception:
            return "#"


def nav_for(user) -> dict:
    """
    Returns single source of truth navigation structure based on user capabilities and role.
    Used by desktop sidebar, tablet rail, mobile bottom bar, and mobile More sheet.
    """
    if not user or not user.is_authenticated:
        return {
            "sidebar_items": [],
            "mobile_bar_items": [],
            "mobile_more_items": [],
        }

    is_hosteler = getattr(user, "is_hosteler", False)
    is_caretaker = getattr(user, "role", None) == Role.CARETAKER
    is_warden = getattr(user, "role", None) == Role.WARDEN
    is_chief_warden = getattr(user, "role", None) == Role.CHIEF_WARDEN
    is_dean = getattr(user, "role", None) == Role.DEAN
    is_admin = getattr(user, "role", None) == Role.ADMIN

    sidebar_items = []

    # 1. Dashboard / Home
    if is_hosteler:
        home_label = "Home"
    elif is_caretaker:
        home_label = "Dashboard"
    elif is_warden:
        home_label = "Hostel dashboard"
    elif is_chief_warden or is_dean:
        home_label = "Campus dashboard"
    elif is_admin:
        home_label = "System dashboard"
    else:
        home_label = "Dashboard"

    sidebar_items.append(
        NavItem(
            key="home",
            label=home_label,
            icon="layout-dashboard",
            url_name="core:home",
            section="dashboard",
        )
    )

    # 2. Tickets
    tickets_label = "My Tickets" if is_hosteler else "Tickets"
    sidebar_items.append(
        NavItem(
            key="tickets",
            label=tickets_label,
            icon="ticket",
            url_name="tickets:list",
            section="tickets",
        )
    )

    # 3. Kanban (Staff operational workflow: Caretaker, Warden, Chief Warden, Dean; NOT Admin, NOT Hosteler)
    if not is_hosteler and not is_admin:
        sidebar_items.append(
            NavItem(
                key="kanban",
                label="Kanban",
                icon="kanban",
                url_name="tickets:kanban",
                section="kanban",
            )
        )

    # 4. Notices (Announcements, Decision D3)
    sidebar_items.append(
        NavItem(
            key="announcements",
            label="Notices",
            icon="megaphone",
            url_name="announcements:list",
            section="announcements",
        )
    )

    # 5. Admin Management Items (Capability-driven, strictly Admin per Section 3.2)
    if user.can(Capability.MANAGE_HOSTELS):
        sidebar_items.append(
            NavItem(
                key="manage_hostels",
                label="Hostels",
                icon="building-2",
                url_name="hostels:manage_hostels",
                section="manage_hostels",
            )
        )
    if user.can(Capability.MANAGE_STAFF):
        sidebar_items.append(
            NavItem(
                key="manage_staff",
                label="Staff",
                icon="users",
                url_name="hostels:manage_staff",
                section="manage_staff",
            )
        )
    if user.can(Capability.MANAGE_RESPONSIBILITY):
        sidebar_items.append(
            NavItem(
                key="manage_responsibility",
                label="Assignments",
                icon="user-check",
                url_name="hostels:manage_responsibility",
                section="manage_responsibility",
            )
        )
    # 6. Trash (Admin only per Section 2 & 6)
    if user.can(Capability.VIEW_TRASH_ALL):
        sidebar_items.append(
            NavItem(
                key="trash",
                label="Trash",
                icon="trash-2",
                url_name="tickets:trash",
                section="trash",
            )
        )

    # 7. Notifications
    sidebar_items.append(
        NavItem(
            key="notifications",
            label="Notifications",
            icon="bell",
            url_name="notifications:list",
            section="notifications",
            badge_key="unread_notifications_count",
        )
    )

    # Mobile Bottom Bar Items (Decisions D1 & D2)
    mobile_bar_items = []
    mobile_more_items = []

    if is_hosteler:
        # Decision D1: Home · Tickets · ＋ Raise · Notices · Profile
        mobile_bar_items = [
            NavItem(key="home", label="Home", icon="home", url_name="core:home", section="dashboard"),
            NavItem(key="tickets", label="Tickets", icon="ticket", url_name="tickets:list", section="tickets"),
            NavItem(key="raise", label="Raise", icon="plus", url_name="tickets:create", section="tickets_create", is_action=True),
            NavItem(key="notices", label="Notices", icon="megaphone", url_name="announcements:list", section="announcements"),
            NavItem(key="profile", label="Profile", icon="user", url_name="accounts:profile", section="profile"),
        ]
        mobile_more_items = []
    elif is_admin:
        # Decision D2: Dashboard · Tickets · Staff · Notices · More
        mobile_bar_items = [
            NavItem(key="dashboard", label="Dashboard", icon="layout-dashboard", url_name="core:home", section="dashboard"),
            NavItem(key="tickets", label="Tickets", icon="ticket", url_name="tickets:list", section="tickets"),
            NavItem(key="staff", label="Staff", icon="users", url_name="hostels:manage_staff", section="manage_staff"),
            NavItem(key="notices", label="Notices", icon="megaphone", url_name="announcements:list", section="announcements"),
            NavItem(key="more", label="More", icon="menu", url_name="", section="more"),
        ]
        mobile_more_items = [
            NavItem(key="manage_hostels", label="Hostels", icon="building-2", url_name="hostels:manage_hostels", section="manage_hostels"),
            NavItem(key="manage_responsibility", label="Assignments", icon="user-check", url_name="hostels:manage_responsibility", section="manage_responsibility"),
            NavItem(key="trash", label="Trash", icon="trash-2", url_name="tickets:trash", section="trash"),
            NavItem(key="profile", label="Profile Settings", icon="user", url_name="accounts:profile", section="profile"),
        ]
    else:
        # Decision D2: Dashboard · Tickets · Kanban · Notices · More
        mobile_bar_items = [
            NavItem(key="dashboard", label="Dashboard", icon="layout-dashboard", url_name="core:home", section="dashboard"),
            NavItem(key="tickets", label="Tickets", icon="ticket", url_name="tickets:list", section="tickets"),
            NavItem(key="kanban", label="Kanban", icon="kanban", url_name="tickets:kanban", section="kanban"),
            NavItem(key="notices", label="Notices", icon="megaphone", url_name="announcements:list", section="announcements"),
            NavItem(key="more", label="More", icon="menu", url_name="", section="more"),
        ]
        mobile_more_items = [
            NavItem(key="profile", label="Profile Settings", icon="user", url_name="accounts:profile", section="profile"),
        ]

    return {
        "sidebar_items": sidebar_items,
        "mobile_bar_items": mobile_bar_items,
        "mobile_more_items": mobile_more_items,
    }
