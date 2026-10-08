import factory

from apps.accounts.factories import UserFactory
from apps.announcements.models import (
    Announcement,
    AnnouncementKind,
    AnnouncementRead,
    AnnouncementSeverity,
    AnnouncementStatus,
)


class AnnouncementFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Announcement

    title = factory.Faker("sentence", nb_words=6)
    body = factory.Faker("paragraph")
    kind = AnnouncementKind.NOTICE
    severity = AnnouncementSeverity.INFO
    author = factory.SubFactory(UserFactory)
    all_hostels = True
    status = AnnouncementStatus.PUBLISHED
    is_pinned = False


class AnnouncementReadFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AnnouncementRead

    announcement = factory.SubFactory(AnnouncementFactory)
    user = factory.SubFactory(UserFactory)
