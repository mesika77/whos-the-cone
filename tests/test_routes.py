import pytest
from fastapi.testclient import TestClient
from database import Player, Game, Session as GameSession
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


def test_results_page_renders_ranked_results(client, closed_session_with_votes):
    """Results page for a closed session renders 200 with player names."""
    session_id = closed_session_with_votes.id
    response = client.get(f"/results/{session_id}", follow_redirects=True)
    assert response.status_code == 200
    assert b"Maor" in response.content
    assert b"Alko" in response.content


def test_results_page_active_session_redirects_to_vote(client, db):
    """Active session redirects to vote page, not results."""
    game = Game(name="ActiveGame")
    player = Player(name="TestPlayer")
    db.add_all([game, player])
    db.flush()
    session = GameSession(game_id=game.id, is_active=1)
    session.participants = [player]
    db.add(session)
    db.commit()

    response = client.get(f"/results/{session.id}", follow_redirects=False)
    assert response.status_code in (302, 303)
    assert response.headers["location"] == f"/vote/{session.id}"
