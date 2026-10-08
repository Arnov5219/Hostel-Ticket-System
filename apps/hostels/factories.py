import factory

from apps.hostels.models import GenderType, Hostel


class HostelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Hostel
        django_get_or_create = ("code",)

    name = factory.Sequence(lambda n: f"Hostel {chr(65 + n % 26)}")
    code = factory.Sequence(lambda n: f"HSTL_{n:03d}")
    gender_type = GenderType.BOYS
    is_active = True


class BlockFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "hostels.Block"

    hostel = factory.SubFactory(HostelFactory)
    name = factory.Sequence(lambda n: f"Block {n}")
    is_active = True


class RoomFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "hostels.Room"

    block = factory.SubFactory(BlockFactory)
    room_number = factory.Sequence(lambda n: f"{100 + n}")
    floor = 1
    capacity = 2
    is_active = True
