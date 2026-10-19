import factory

from apps.hostels.models import GenderType, Hostel, Room


class HostelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Hostel
        django_get_or_create = ("code",)

    name = factory.Sequence(lambda n: f"Boys Hostel {n}")
    code = factory.Sequence(lambda n: f"BH-{n}")
    gender_type = GenderType.BOYS
    is_active = True


class RoomFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Room

    hostel = factory.SubFactory(HostelFactory)
    room_number = factory.Sequence(lambda n: f"{101 + n % 40}")
    floor = 1
    capacity = 2
    is_active = True
