import factory

from apps.accounts.factories import UserFactory
from apps.hostels.factories import HostelFactory, RoomFactory
from apps.tickets.models import (
    Category,
    Priority,
    Status,
    Ticket,
    TicketComment,
)
from apps.tickets.services.numbering import generate_ticket_number


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category
        django_get_or_create = ("name",)

    name = factory.Sequence(lambda n: f"Category {n}")
    icon = "ticket"
    default_priority = Priority.MEDIUM
    is_active = True


class TicketFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Ticket

    ticket_no = factory.LazyFunction(generate_ticket_number)
    title = factory.Faker("sentence", nb_words=5)
    description = factory.Faker("paragraph")
    category = factory.SubFactory(CategoryFactory)
    priority = Priority.MEDIUM
    status = Status.OPEN
    reporter = factory.SubFactory(UserFactory)
    hostel = factory.SubFactory(HostelFactory)
    room = factory.SubFactory(RoomFactory)
    current_level = 1


class TicketCommentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TicketComment

    ticket = factory.SubFactory(TicketFactory)
    author = factory.SubFactory(UserFactory)
    body = factory.Faker("sentence")
    is_internal = False
