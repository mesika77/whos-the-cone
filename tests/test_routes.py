import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_results_session_not_found_redirects_home():
    """Non-existent session id redirects to /."""
    response = client.get("/results/99999", follow_redirects=False)
    assert response.status_code in (302, 303)
    assert response.headers["location"] == "/"


def test_results_latest_redirects_somewhere():
    """
    /results/latest always redirects: to / if no closed sessions exist,
    or to /results/<id> if one does.
    """
    response = client.get("/results/latest", follow_redirects=False)
    assert response.status_code in (302, 303)
    location = response.headers["location"]
    # Must redirect to either / or a specific results page — not anything else
    assert location == "/" or (location.startswith("/results/") and location != "/results/latest")


def test_results_latest_follows_to_valid_page():
    """Following /results/latest always ends at a 200 page."""
    response = client.get("/results/latest", follow_redirects=True)
    assert response.status_code == 200
    # If it rendered the results page, it must contain ranked player data
    # If it redirected home (no sessions), the home page content appears
    assert b"WHO" in response.content or b"Create New Session" in response.content


def test_results_page_not_found_redirects():
    """A missing session ID causes redirect to home."""
    response = client.get("/results/0", follow_redirects=False)
    assert response.status_code in (302, 303)
    assert response.headers["location"] == "/"
