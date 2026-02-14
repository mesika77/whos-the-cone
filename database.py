from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, Table
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime

DATABASE_URL = "sqlite:///./whos_the_cone.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- ASSOCIATION TABLE (Many-to-Many) ---
# This tracks WHICH players were in a specific session
session_participants = Table('session_participants', Base.metadata,
    Column('session_id', Integer, ForeignKey('sessions.id')),
    Column('player_id', Integer, ForeignKey('players.id'))
)

# --- MODELS ---
class Player(Base):
    __tablename__ = "players"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    
class Game(Base):
    __tablename__ = "games"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)

class Session(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=datetime.now)
    game_id = Column(Integer, ForeignKey("games.id"))
    is_active = Column(Integer, default=1) # 1 = Open for voting, 0 = Closed
    
    game = relationship("Game")
    # This magic line connects Session to Players
    participants = relationship("Player", secondary=session_participants, backref="sessions")
    votes = relationship("Vote", back_populates="session", cascade="all, delete-orphan")

class Vote(Base):
    __tablename__ = "votes"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"))
    voter_id = Column(Integer, ForeignKey("players.id"))       # Who cast the vote
    target_player_id = Column(Integer, ForeignKey("players.id")) # Who they ranked
    rank_score = Column(Integer)  # 1 (Cone) to 4 (King)

    session = relationship("Session", back_populates="votes")
    voter = relationship("Player", foreign_keys=[voter_id])
    target = relationship("Player", foreign_keys=[target_player_id])

def init_db():
    Base.metadata.drop_all(bind=engine) # RESET DB for new structure
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Seed Data
    players = ["Maor", "Alko", "Becker", "Regev"]
    for p in players: db.add(Player(name=p))
    
    games = ["FIFA", "Rainbow 6 Siege", "PUBG", "Call Of Duty", "Battlefield"]
    for g in games: db.add(Game(name=g))
    
    db.commit()
    db.close()
    print("✅ Database upgraded & reset!")

if __name__ == "__main__":
    init_db()