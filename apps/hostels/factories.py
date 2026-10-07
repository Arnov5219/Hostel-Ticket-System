import factory

from apps.hostels.models import GenderType, Hostel


class HostelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Hostel
        django_get_or_create = ("code",)

    name = factory.Sequence(lambda n: f"Hostel {chr(65 + n % 26)}")
    code = factory.Sequence(lambda n: f"HSTL_{n:03d}")
    gender_type = GenderType.BOYS
    address = factory.Faker("address")
    is_active = True
