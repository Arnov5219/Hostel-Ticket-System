import factory

from apps.accounts.factories import UserFactory
from apps.hostels.factories import HostelFactory
from apps.tickets.models import (
    Category,
    CommentScope,
    CriticalityRule,
    Priority,
    Status,
    Ticket,
    TicketComment,
    TicketRepost,
    TicketVisibility,
)
from apps.tickets.services.numbering import generate_ticket_number


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category
        django_get_or_create = ("name",)

    name = factory.Sequence(lambda n: f"Category {n}")
    icon = "ticket"
    default_priority = Priority.MEDIUM
    allow_community = True
    is_active = True


class TicketFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Ticket

    ticket_no = factory.LazyFunction(generate_ticket_number)
    title = factory.Faker("sentence", nb_words=5)
    description = factory.Faker("paragraph")
    category = factory.SubFactory(CategoryFactory)
    visibility = TicketVisibility.PRIVATE
    base_priority = Priority.MEDIUM
    priority = Priority.MEDIUM
    status = Status.OPEN
    reporter = factory.SubFactory(UserFactory)
    hostel = factory.SubFactory(HostelFactory)
    current_level = 1
    repost_count = 0


class TicketRepostFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TicketRepost

    ticket = factory.SubFactory(TicketFactory)
    user = factory.SubFactory(UserFactory)
    note = ""


class TicketCommentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TicketComment

    ticket = factory.SubFactory(TicketFactory)
    author = factory.SubFactory(UserFactory)
    body = factory.Faker("sentence")
    scope = CommentScope.PRIVATE


class CriticalityRuleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CriticalityRule

    min_reposts = factory.Sequence(lambda n: n + 1)
    bump_levels = 1

