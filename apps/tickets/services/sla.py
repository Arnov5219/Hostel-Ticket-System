from apps.tickets.models import Priority, SLAPolicy

DEFAULT_SLA_HOURS = {
    Priority.URGENT: {1: 2, 2: 2, 3: 4, 4: 4},
    Priority.HIGH: {1: 8, 2: 8, 3: 12, 4: 12},
    Priority.MEDIUM: {1: 24, 2: 24, 3: 24, 4: 24},
    Priority.LOW: {1: 48, 2: 48, 3: 48, 4: 48},
}


def hours_for(priority: str, level: int) -> int:
    """
    Returns SLA hours for priority and escalation level.
    Reads from SLAPolicy table; falls back to built-in default table if row is missing.
    A deleted or empty table will never crash routing or escalation.
    """
    try:
        policy = SLAPolicy.objects.filter(priority=priority, level=level).first()
        if policy and policy.hours:
            return policy.hours
    except Exception:
        pass

    safe_level = max(1, min(4, int(level)))
    priority_table = DEFAULT_SLA_HOURS.get(priority, DEFAULT_SLA_HOURS[Priority.MEDIUM])
    return priority_table.get(safe_level, 24)
