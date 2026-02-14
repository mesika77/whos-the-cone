from fastapi import FastAPI, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from database import SessionLocal, Player, Game, Session as GameSession, Vote
from datetime import datetime
from typing import List, Optional
import json

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return RedirectResponse(url="/static/cone.png", status_code=302)


def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# --- 1. HOME (LOBBY) ---
@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    # Show active sessions for people to join
    active_sessions = db.query(GameSession).filter(GameSession.is_active == 1).order_by(GameSession.date.desc()).all()
    games = db.query(Game).all()
    players = db.query(Player).all()
    
    return templates.TemplateResponse("index.html", {
        "request": request, "active_sessions": active_sessions, 
        "games": games, "players": players
    })

# --- 2. CREATE SESSION (HOST) ---
@app.post("/create_session")
def create_session(
    game_id: int = Form(...),
    player_ids: List[int] = Form(...), # Checkboxes from form
    db: Session = Depends(get_db)
):
    # Create Session
    new_session = GameSession(game_id=game_id, date=datetime.now())
    
    # Add Participants
    participants = db.query(Player).filter(Player.id.in_(player_ids)).all()
    new_session.participants = participants
    
    db.add(new_session)
    db.commit()
    return RedirectResponse(url=f"/vote/{new_session.id}", status_code=303)

# --- 3. VOTING ROOM ---
@app.get("/vote/{session_id}", response_class=HTMLResponse)
def vote_room(request: Request, session_id: int, db: Session = Depends(get_db)):
    session = db.get(GameSession, session_id)
    if not session or not session.game:
        return RedirectResponse(url="/", status_code=303)
    if session.is_active == 0:
        return RedirectResponse(url="/stats", status_code=303)
    error = request.query_params.get("error")
    return templates.TemplateResponse("vote.html", {
        "request": request, "session": session, "error": error
    })

@app.post("/submit_vote")
def submit_vote(
    session_id: int = Form(...),
    voter_id: int = Form(...),
    rankings: str = Form(...), # JSON string of IDs
    db: Session = Depends(get_db)
):
    session = db.get(GameSession, session_id)
    if not session or not session.game:
        return RedirectResponse(url="/", status_code=303)
    if session.is_active == 0:
        return RedirectResponse(url="/stats", status_code=303)
    existing_vote = db.query(Vote).filter(
        Vote.session_id == session_id,
        Vote.voter_id == voter_id
    ).first()
    if existing_vote:
        return RedirectResponse(url=f"/vote/{session_id}?error=already_voted", status_code=303)
    participant_ids = [p.id for p in session.participants]
    if voter_id not in participant_ids:
        return RedirectResponse(url=f"/vote/{session_id}?error=not_participant", status_code=303)

    ranked_ids = json.loads(rankings) # [WinnerID, ..., LoserID]
    num_players = len(ranked_ids)
    for index, target_id in enumerate(ranked_ids):
        score = num_players - index
        vote = Vote(
            session_id=session_id,
            voter_id=voter_id,
            target_player_id=int(target_id),
            rank_score=score
        )
        db.add(vote)
    db.commit()

    voter_ids = {v[0] for v in db.query(Vote.voter_id).filter(Vote.session_id == session_id).distinct().all()}
    if voter_ids >= set(participant_ids):
        session.is_active = 0
        db.commit()
    return RedirectResponse(url="/stats", status_code=303)

# --- 4. STATS & ADMIN PAGE ---
@app.get("/stats", response_class=HTMLResponse)
def stats_page(
    request: Request,
    game_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    games = db.query(Game).all()
    sessions_query = db.query(GameSession).order_by(GameSession.date.desc())
    if game_id is not None:
        sessions_query = sessions_query.filter(GameSession.game_id == game_id)
    sessions = sessions_query.all()
    session_ids = [s.id for s in sessions]

    players = db.query(Player).all()
    leaderboard = []
    for p in players:
        if session_ids:
            total = db.query(func.sum(Vote.rank_score)).filter(
                Vote.target_player_id == p.id,
                Vote.session_id.in_(session_ids)
            ).scalar() or 0
            cone_count = db.query(Vote).filter(
                Vote.target_player_id == p.id,
                Vote.rank_score == 1,
                Vote.session_id.in_(session_ids)
            ).count()
        else:
            total = 0
            cone_count = 0

        king_count = 0
        for s in sessions:
            n = len(s.participants)
            king_count += db.query(Vote).filter(
                Vote.target_player_id == p.id,
                Vote.session_id == s.id,
                Vote.rank_score == n
            ).count()

        sessions_participated = sum(1 for s in sessions if p in s.participants)

        leaderboard.append({
            "id": p.id,
            "name": p.name,
            "score": total,
            "sessions_participated": sessions_participated,
            "cone_count": cone_count,
            "king_count": king_count,
        })
    leaderboard.sort(key=lambda x: x["score"], reverse=True)

    return templates.TemplateResponse("stats.html", {
        "request": request,
        "sessions": sessions,
        "leaderboard": leaderboard,
        "games": games,
        "selected_game_id": game_id,
    })

# --- 5. PLAYER STATS PAGE ---
@app.get("/player/{player_id}", response_class=HTMLResponse)
def player_page(
    request: Request,
    player_id: int,
    game_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    player = db.get(Player, player_id)
    if not player:
        return RedirectResponse(url="/stats", status_code=303)

    games = db.query(Game).all()
    sessions_query = db.query(GameSession).order_by(GameSession.date.desc())
    if game_id is not None:
        sessions_query = sessions_query.filter(GameSession.game_id == game_id)
    sessions = sessions_query.all()
    session_ids = [s.id for s in sessions]

    # Sessions this player participated in (within filter)
    player_sessions = [s for s in sessions if player in s.participants]

    # Overall stats (filtered sessions)
    if session_ids:
        total = db.query(func.sum(Vote.rank_score)).filter(
            Vote.target_player_id == player.id,
            Vote.session_id.in_(session_ids)
        ).scalar() or 0
        cone_count = db.query(Vote).filter(
            Vote.target_player_id == player.id,
            Vote.rank_score == 1,
            Vote.session_id.in_(session_ids)
        ).count()
    else:
        total = 0
        cone_count = 0

    king_count = 0
    for s in sessions:
        n = len(s.participants)
        king_count += db.query(Vote).filter(
            Vote.target_player_id == player.id,
            Vote.session_id == s.id,
            Vote.rank_score == n
        ).count()

    overall = {
        "score": total,
        "king_count": king_count,
        "cone_count": cone_count,
        "sessions_count": len(player_sessions),
    }

    # Per-game stats (games this player participated in, within filter)
    by_game = []
    seen_game_ids = set()
    for s in player_sessions:
        g = s.game
        if not g or g.id in seen_game_ids:
            continue
        seen_game_ids.add(g.id)
        g_sessions = [sess for sess in player_sessions if sess.game_id == g.id]
        g_session_ids = [sess.id for sess in g_sessions]
        g_score = db.query(func.sum(Vote.rank_score)).filter(
            Vote.target_player_id == player.id,
            Vote.session_id.in_(g_session_ids)
        ).scalar() or 0
        g_kings = sum(
            db.query(Vote).filter(
                Vote.target_player_id == player.id,
                Vote.session_id == sess.id,
                Vote.rank_score == len(sess.participants)
            ).count()
            for sess in g_sessions
        )
        g_cones = db.query(Vote).filter(
            Vote.target_player_id == player.id,
            Vote.rank_score == 1,
            Vote.session_id.in_(g_session_ids)
        ).count()
        by_game.append({
            "game_id": g.id,
            "game_name": g.name,
            "score": g_score,
            "king_count": g_kings,
            "cone_count": g_cones,
            "sessions_count": len(g_sessions),
        })
    by_game.sort(key=lambda x: x["score"], reverse=True)

    # Session history: score, was_king, was_cone, rank_in_session per session
    session_history = []
    for s in player_sessions:
        n = len(s.participants)
        score_in_session = db.query(func.sum(Vote.rank_score)).filter(
            Vote.target_player_id == player.id,
            Vote.session_id == s.id
        ).scalar() or 0
        was_king = db.query(Vote).filter(
            Vote.target_player_id == player.id,
            Vote.session_id == s.id,
            Vote.rank_score == n
        ).count() > 0
        was_cone = db.query(Vote).filter(
            Vote.target_player_id == player.id,
            Vote.session_id == s.id,
            Vote.rank_score == 1
        ).count() > 0
        # Rank in session: compute each participant's score, sort desc, find position
        participant_scores = []
        for p in s.participants:
            p_score = db.query(func.sum(Vote.rank_score)).filter(
                Vote.target_player_id == p.id,
                Vote.session_id == s.id
            ).scalar() or 0
            participant_scores.append((p.id, p_score))
        participant_scores.sort(key=lambda x: x[1], reverse=True)
        rank_in_session = 1
        for i, (pid, _) in enumerate(participant_scores, 1):
            if pid == player.id:
                rank_in_session = i
                break
        session_history.append({
            "session": s,
            "game_name": s.game.name if s.game else "—",
            "date": s.date,
            "score_in_session": score_in_session,
            "was_king": was_king,
            "was_cone": was_cone,
            "rank_in_session": rank_in_session,
        })
    session_history.sort(key=lambda x: x["date"], reverse=True)

    # Chart: score over time (one point per player session, oldest first for chart order)
    chart_over_time = []
    for h in reversed(session_history):
        chart_over_time.append({
            "date_label": h["date"].strftime("%Y-%m-%d %H:%M"),
            "score": h["score_in_session"],
            "king": 1 if h["was_king"] else 0,
            "cone": 1 if h["was_cone"] else 0,
        })

    # JSON for chart scripts (dates and session_history items need serialization)
    chart_over_time_js = json.dumps([
        {"date_label": d["date_label"], "score": d["score"], "king": d["king"], "cone": d["cone"]}
        for d in chart_over_time
    ])
    by_game_js = json.dumps([{"game_name": g["game_name"], "score": g["score"]} for g in by_game])

    return templates.TemplateResponse("player.html", {
        "request": request,
        "player": player,
        "games": games,
        "selected_game_id": game_id,
        "overall": overall,
        "by_game": by_game,
        "session_history": session_history,
        "chart_over_time": chart_over_time,
        "chart_over_time_js": chart_over_time_js,
        "by_game_js": by_game_js,
    })

@app.post("/delete_session")
def delete_session(
    session_id: int = Form(...),
    game_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    session = db.get(GameSession, session_id)
    if session:
        db.delete(session)
        db.commit()
    url = "/stats" + (f"?game_id={game_id}" if game_id is not None else "")
    return RedirectResponse(url=url, status_code=303)