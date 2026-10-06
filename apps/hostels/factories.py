import factory

from apps.hostels.models import Block, GenderType, Hostel, Room


class HostelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Hostel
        django_get_or_create = ("code",)

    name = factory.Sequence(lambda n: f"Hostel {chr(65 + n % 26)}")
    code = factory.Sequence(lambda n: f"HSTL_{n:03d}")
    gender_type = GenderType.BOYS
    address = factory.Faker("address")
    is_active = True


class BlockFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Block
        django_get_or_create = ("hostel", "name")

    hostel = factory.SubFactory(HostelFactory)
    name = factory.Sequence(lambda n: f"Block {chr(65 + n % 26)}")


class RoomFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Room
        django_get_or_create = ("block", "room_number")

    block = factory.SubFactory(BlockFactory)
    room_number = factory.Sequence(lambda n: f"{100 + n}")
    floor = 1
    capacity = 2
