import factory

from apps.accounts.models import Role, User


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ("login_id",)

    login_id = factory.Sequence(lambda n: f"USER{n:04d}")
    full_name = factory.Faker("name")
    email = factory.Faker("email")
    phone = factory.Faker("phone_number")
    role = Role.HOSTELER
    escalation_level = None
    is_active = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        password = kwargs.pop("password", "pass1234")
        with_residence = kwargs.pop("with_residence", True)
        user = super()._create(model_class, *args, **kwargs)
        user.set_password(password)

        if user.role == Role.HOSTELER and with_residence and not user.has_residence:
            from django.utils import timezone
            from apps.hostels.factories import BlockFactory, HostelFactory, RoomFactory

            if not user.hostel:
                user.hostel = HostelFactory()
            if not user.room:
                block = BlockFactory(hostel=user.hostel)
                user.room = RoomFactory(block=block)
            user.residence_set_at = timezone.now()

        user.save()
        return user
