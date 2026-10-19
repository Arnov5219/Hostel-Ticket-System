import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_health_check_endpoint(client):
    """Verify lightweight health check endpoint returns 200 and json status ok."""
    url = reverse("core:health")
    response = client.get(url)
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "app": "Hostel Ticket System"}
