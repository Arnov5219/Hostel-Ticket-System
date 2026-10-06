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
        user = super()._create(model_class, *args, **kwargs)
        user.set_password(password)
        user.save()
        return user
