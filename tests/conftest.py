import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from database import Base, Player, Game, Session as GameSession, Vote
from main import app, get_db

# In-memory SQLite for tests — StaticPool ensures all connections share one in-memory DB
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def closed_session_with_votes(db):
    """Creates a closed session: Maor ranks #1, Alko ranks #2 (the cone)."""
    game = Game(name="TestGame")
    maor = Player(name="Maor")
    alko = Player(name="Alko")
    db.add_all([game, maor, alko])
    db.flush()

    session = GameSession(game_id=game.id, is_active=0)
    session.participants = [maor, alko]
    db.add(session)
    db.flush()

    # Maor votes: Maor=2pts (king), Alko=1pt (cone)
    db.add(Vote(session_id=session.id, voter_id=maor.id, target_player_id=maor.id, rank_score=2))
    db.add(Vote(session_id=session.id, voter_id=maor.id, target_player_id=alko.id, rank_score=1))
    # Alko votes: Maor=2pts (king), Alko=1pt (cone)
    db.add(Vote(session_id=session.id, voter_id=alko.id, target_player_id=maor.id, rank_score=2))
    db.add(Vote(session_id=session.id, voter_id=alko.id, target_player_id=alko.id, rank_score=1))
    db.commit()
    return session
