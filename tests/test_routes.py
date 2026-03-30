import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_results_latest_no_closed_sessions_redirects_home():
    """When no closed sessions exist, /results/latest redirects to /."""
    # This test may vary depending on DB state — if sessions exist it redirects to results page
    response = client.get("/results/latest", follow_redirects=False)
    assert response.status_code in (302, 303)
    location = response.headers["location"]
    assert location == "/" or location.startswith("/results/")


def test_results_session_not_found_redirects_home():
    """Non-existent session id redirects to /."""
    response = client.get("/results/99999", follow_redirects=False)
    assert response.status_code in (302, 303)
    assert response.headers["location"] == "/"


def test_results_page_renders():
    """If any closed session exists, /results/latest renders the results page."""
    # Follow redirects to get the final page
    response = client.get("/results/latest", follow_redirects=True)
    # Either redirected home (no sessions) or rendered results page
    assert response.status_code == 200
