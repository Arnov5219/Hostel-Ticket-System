from dataclasses import dataclass
from typing import Optional
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
    badge_key: Optional[str] = None
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
    is_cw_or_admin = getattr(user, "role", None) in [Role.CHIEF_WARDEN, Role.ADMIN]

    sidebar_items = []

    # 1. Dashboard / Home
    home_label = "Home" if is_hosteler else "Dashboard"
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

    # 3. Kanban (Staff only)
    if not is_hosteler:
        sidebar_items.append(
            NavItem(
                key="kanban",
                label="Kanban",
                icon="kanban",
                url_name="tickets:kanban",
                section="kanban",
            )
        )

    # 4. Announcements
    sidebar_items.append(
        NavItem(
            key="announcements",
            label="Announcements",
            icon="megaphone",
            url_name="announcements:list",
            section="announcements",
        )
    )

    # 5. Admin / Chief Warden Management Items
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
                label="Staff Management",
                icon="users",
                url_name="hostels:manage_staff",
                section="manage_staff",
            )
        )
    if user.can(Capability.MANAGE_RESPONSIBILITY):
        sidebar_items.append(
            NavItem(
                key="manage_responsibility",
                label="Hostel Responsibility",
                icon="user-check",
                url_name="hostels:manage_responsibility",
                section="manage_responsibility",
            )
        )
    if user.can(Capability.MANAGE_TICKET_SETTINGS):
        sidebar_items.append(
            NavItem(
                key="manage_settings",
                label="Ticket Settings",
                icon="sliders-horizontal",
                url_name="tickets:manage_settings",
                section="manage_settings",
            )
        )

    # 6. Trash (Warden, Chief Warden, Admin)
    if is_warden or is_cw_or_admin:
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

    # Mobile Bottom Bar Items
    mobile_bar_items = []
    mobile_more_items = []

    if is_hosteler:
        # Hosteler = Home · My tickets · ＋ Raise · News · More
        mobile_bar_items = [
            NavItem(key="home", label="Home", icon="home", url_name="core:home", section="dashboard"),
            NavItem(key="tickets", label="My Tickets", icon="ticket", url_name="tickets:list", section="tickets"),
            NavItem(key="raise", label="Raise", icon="plus", url_name="tickets:create", section="tickets_create", is_action=True),
            NavItem(key="news", label="News", icon="megaphone", url_name="announcements:list", section="announcements"),
            NavItem(key="more", label="More", icon="menu", url_name="", section="more"),
        ]
        mobile_more_items = [
            NavItem(key="notifications", label="Notifications", icon="bell", url_name="notifications:list", section="notifications", badge_key="unread_notifications_count"),
            NavItem(key="profile", label="Profile & Residence", icon="user", url_name="accounts:profile", section="profile"),
        ]
    else:
        # Staff = Dashboard · Tickets · Kanban · Alerts · More
        mobile_bar_items = [
            NavItem(key="dashboard", label="Dashboard", icon="layout-dashboard", url_name="core:home", section="dashboard"),
            NavItem(key="tickets", label="Tickets", icon="ticket", url_name="tickets:list", section="tickets"),
            NavItem(key="kanban", label="Kanban", icon="kanban", url_name="tickets:kanban", section="kanban"),
            NavItem(key="alerts", label="Alerts", icon="bell", url_name="notifications:list", section="notifications", badge_key="unread_notifications_count"),
            NavItem(key="more", label="More", icon="menu", url_name="", section="more"),
        ]
        mobile_more_items = [
            NavItem(key="announcements", label="Announcements", icon="megaphone", url_name="announcements:list", section="announcements"),
        ]
        if user.can(Capability.MANAGE_HOSTELS):
            mobile_more_items.append(NavItem(key="manage_hostels", label="Hostels Management", icon="building-2", url_name="hostels:manage_hostels", section="manage_hostels"))
        if user.can(Capability.MANAGE_STAFF):
            mobile_more_items.append(NavItem(key="manage_staff", label="Staff Management", icon="users", url_name="hostels:manage_staff", section="manage_staff"))
        if user.can(Capability.MANAGE_RESPONSIBILITY):
            mobile_more_items.append(NavItem(key="manage_responsibility", label="Hostel Responsibility", icon="user-check", url_name="hostels:manage_responsibility", section="manage_responsibility"))
        if user.can(Capability.MANAGE_TICKET_SETTINGS):
            mobile_more_items.append(NavItem(key="manage_settings", label="Ticket Settings", icon="sliders-horizontal", url_name="tickets:manage_settings", section="manage_settings"))
        if is_warden or is_cw_or_admin:
            mobile_more_items.append(NavItem(key="trash", label="Trash Log", icon="trash-2", url_name="tickets:trash", section="trash"))
        mobile_more_items.append(NavItem(key="profile", label="Profile Settings", icon="user", url_name="accounts:profile", section="profile"))

    return {
        "sidebar_items": sidebar_items,
        "mobile_bar_items": mobile_bar_items,
        "mobile_more_items": mobile_more_items,
    }
