import pytest

from apps.accounts.models import Role, User
from apps.hostels.models import GenderType, Hostel
from apps.hostels.services import generate_rooms, natural_sort_key


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

    def test_options_floors_endpoint_removed_404(self, client):
        response = client.get("/hostels/options/floors/?hostel=1")
        assert response.status_code == 404

    def test_options_rooms_endpoint_removed_404(self, client):
        response = client.get("/hostels/options/rooms/?hostel=1&floor=2")
        assert response.status_code == 404

    def test_manage_rooms_admin_view_removed_404(self, client):
        admin_user = User.objects.create_user(
            login_id="adm_rooms", role=Role.ADMIN, password="password123", is_staff=True
        )
        client.force_login(admin_user)
        resp = client.get("/manage/rooms/")
        assert resp.status_code == 404
