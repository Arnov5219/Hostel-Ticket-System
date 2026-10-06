import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_ui_kit_page_renders(client):
    response = client.get(reverse("core:ui_kit"))
    assert response.status_code == 200
    assert b"Design System Showcase" in response.content
    assert b"status-pill" in response.content
    assert b"prio-dot" in response.content
    assert b"btn-primary" in response.content
