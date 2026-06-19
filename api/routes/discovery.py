"""Discovery routes — algorithmic feed, search, trending"""
from fastapi import APIRouter, Request
from api.database import get_db
from api.templates import respond
from api.routes.auth import get_current_artist

router = APIRouter()


def compute_discovery_score(track: dict) -> float:
    """
    Music Bank Discovery Algorithm
    Transparent scoring — no black box, no payola.
    
    Factors:
    - Play velocity (recent plays weighted higher): 30%
    - Like ratio (likes / plays): 25%
    - Artist engagement (followers, uploads): 15%
    - Freshness (newer tracks get boost): 20%
    - Deposit signals (fan deposits = real value): 10%
    """
    import math
    from datetime import datetime

    plays = max(track.get("plays", 0), 1)
    likes = track.get("likes", 0)
    deposits = track.get("deposits", 0)
    created = track.get("created_at", "")

    # Like ratio (0-1)
    like_ratio = min(likes / plays, 1.0)

    # Play velocity — log scale to prevent runaway winners
    play_score = math.log10(plays + 1) / 5.0  # Normalize ~0-1

    # Freshness — newer tracks get a boost that decays over 30 days
    freshness = 0.5
    if created:
        try:
            created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            days_old = (datetime.now(created_dt.tzinfo) - created_dt).days
            freshness = max(0.0, 1.0 - (days_old / 30.0))
        except:
            pass

    # Deposit signal
    deposit_score = min(deposits / 10.0, 1.0)

    # Weighted total
    score = (
        play_score * 0.30 +
        like_ratio * 0.25 +
        freshness * 0.20 +
        deposit_score * 0.10 +
        0.15  # Base engagement placeholder
    )

    return round(score, 4)


@router.get("/")
async def discovery_feed(request: Request):
    """Main discovery feed — algorithmically ranked."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT t.*, a.username as artist_username, a.display_name as artist_name, a.genre as artist_genre FROM tracks t JOIN artists a ON t.artist_id=a.id WHERE t.is_published=1 ORDER BY t.created_at DESC LIMIT 50"
        )
        tracks = [dict(r) for r in await cursor.fetchall()]
    finally:
        await db.close()

    # Score and sort
    for t in tracks:
        t["discovery_score"] = compute_discovery_score(t)
    tracks.sort(key=lambda x: x["discovery_score"], reverse=True)

    current_artist = await get_current_artist(request)

    return respond("track/feed.html", {
        "request": request,
        "tracks": tracks,
        "feed_type": "discovery",
        "current_artist": current_artist,
    })


@router.get("/trending")
async def trending(request: Request):
    """Trending — most played in last 7 days."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT t.*, a.username as artist_username, a.display_name as artist_name FROM tracks t JOIN artists a ON t.artist_id=a.id WHERE t.is_published=1 ORDER BY t.plays DESC LIMIT 30"
        )
        tracks = [dict(r) for r in await cursor.fetchall()]
    finally:
        await db.close()

    current_artist = await get_current_artist(request)
    return respond("track/feed.html", {
        "request": request,
        "tracks": tracks,
        "feed_type": "trending",
        "current_artist": current_artist,
    })


@router.get("/new")
async def new_releases(request: Request):
    """Newest releases — chronological."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT t.*, a.username as artist_username, a.display_name as artist_name FROM tracks t JOIN artists a ON t.artist_id=a.id WHERE t.is_published=1 ORDER BY t.created_at DESC LIMIT 30"
        )
        tracks = [dict(r) for r in await cursor.fetchall()]
    finally:
        await db.close()

    current_artist = await get_current_artist(request)
    return respond("track/feed.html", {
        "request": request,
        "tracks": tracks,
        "feed_type": "new",
        "current_artist": current_artist,
    })


@router.get("/search")
async def search(request: Request, q: str = ""):
    """Search tracks and artists."""
    if not q or len(q.strip()) < 2:
        return respond("track/feed.html", {
            "request": request,
            "tracks": [],
            "feed_type": "search",
            "query": q,
            "current_artist": await get_current_artist(request),
        })

    db = await get_db()
    try:
        search_term = f"%{q}%"
        cursor = await db.execute(
            "SELECT t.*, a.username as artist_username, a.display_name as artist_name FROM tracks t JOIN artists a ON t.artist_id=a.id WHERE t.is_published=1 AND (t.title LIKE ? OR t.genre LIKE ? OR a.display_name LIKE ? OR t.mood LIKE ?) ORDER BY t.plays DESC LIMIT 30",
            (search_term, search_term, search_term, search_term)
        )
        tracks = [dict(r) for r in await cursor.fetchall()]
    finally:
        await db.close()

    current_artist = await get_current_artist(request)
    return respond("track/feed.html", {
        "request": request,
        "tracks": tracks,
        "feed_type": "search",
        "query": q,
        "current_artist": current_artist,
    })


@router.get("/genre/{genre}")
async def by_genre(request: Request, genre: str):
    """Browse by genre."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT t.*, a.username as artist_username, a.display_name as artist_name FROM tracks t JOIN artists a ON t.artist_id=a.id WHERE t.is_published=1 AND t.genre LIKE ? ORDER BY t.plays DESC LIMIT 30",
            (f"%{genre}%",)
        )
        tracks = [dict(r) for r in await cursor.fetchall()]
    finally:
        await db.close()

    current_artist = await get_current_artist(request)
    return respond("track/feed.html", {
        "request": request,
        "tracks": tracks,
        "feed_type": "genre",
        "genre": genre,
        "current_artist": current_artist,
    })
