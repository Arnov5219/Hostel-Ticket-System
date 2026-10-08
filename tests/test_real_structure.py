import pytest
from django.urls import reverse

from apps.accounts.models import Role, User
from apps.hostels.models import GenderType, Hostel, Room
from apps.hostels.services import generate_rooms, natural_sort_key, room_options


@pytest.mark.django_db
class TestRealHostelStructure:
    def test_natural_sort_key(self):
        codes = ["BH-10", "BH-2", "BH-1", "BH-12", "BH-3"]
        sorted_codes = sorted(codes, key=natural_sort_key)
        assert sorted_codes == ["BH-1", "BH-2", "BH-3", "BH-10", "BH-12"]

    def test_generate_rooms_idempotent(self):
        hostel = Hostel.objects.create(name="Boys Hostel 1", code="BH-1", gender_type=GenderType.BOYS)
        count1 = generate_rooms(hostel, floors=3, rooms_per_floor=40, capacity=2, first_floor=1)
        assert count1 == 120
        assert hostel.rooms.count() == 120

        # Running again should create 0 new rooms
        count2 = generate_rooms(hostel, floors=3, rooms_per_floor=40, capacity=2, first_floor=1)
        assert count2 == 0
        assert hostel.rooms.count() == 120

        # Check room numbering format
        floor_1_rooms = list(hostel.rooms.filter(floor=1).order_by("room_number").values_list("room_number", flat=True))
        assert floor_1_rooms[0] == "101"
        assert floor_1_rooms[-1] == "140"
        assert len(floor_1_rooms) == 40

        floor_3_rooms = list(hostel.rooms.filter(floor=3).order_by("room_number").values_list("room_number", flat=True))
        assert floor_3_rooms[0] == "301"
        assert floor_3_rooms[-1] == "340"

    def test_options_floors_endpoint_public(self, client):
        hostel = Hostel.objects.create(name="Boys Hostel 1", code="BH-1", gender_type=GenderType.BOYS)
        generate_rooms(hostel, floors=3, rooms_per_floor=40)

        url = reverse("hostels:options_floors") + f"?hostel={hostel.id}"
        response = client.get(url)
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "Floor 1" in content
        assert "Floor 2" in content
        assert "Floor 3" in content

    def test_options_rooms_chips_and_options_format(self, client):
        hostel = Hostel.objects.create(name="Boys Hostel 1", code="BH-1", gender_type=GenderType.BOYS)
        generate_rooms(hostel, floors=3, rooms_per_floor=40)

        # Chips format (default)
        url_chips = reverse("hostels:options_rooms") + f"?hostel={hostel.id}&floor=2"
        resp_chips = client.get(url_chips)
        assert resp_chips.status_code == 200
        assert "room-chip" in resp_chips.content.decode("utf-8")
        assert "214" in resp_chips.content.decode("utf-8")

        # Select options format
        url_opts = reverse("hostels:options_rooms") + f"?hostel={hostel.id}&floor=2&format=options"
        resp_opts = client.get(url_opts)
        assert resp_opts.status_code == 200
        content_opts = resp_opts.content.decode("utf-8")
        assert "<option value=" in content_opts
        assert "Room 214 · Floor 2" in content_opts

    def test_manage_rooms_admin_view(self, client):
        admin_user = User.objects.create_user(
            login_id="adm_rooms", role=Role.ADMIN, password="password123", is_staff=True
        )
        hostel = Hostel.objects.create(name="Boys Hostel 1", code="BH-1", gender_type=GenderType.BOYS)
        generate_rooms(hostel, floors=3, rooms_per_floor=40)

        client.force_login(admin_user)
        url = reverse("hostels:manage_rooms")
        resp = client.get(url)
        assert resp.status_code == 200
        assert "Room Management" in resp.content.decode("utf-8")

        # Filter by floor
        resp_floor = client.get(f"{url}?hostel={hostel.id}&floor=2")
        assert resp_floor.status_code == 200
        assert resp_floor.context["page_obj"].paginator.count == 40
