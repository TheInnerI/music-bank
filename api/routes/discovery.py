"""Discovery routes — algorithmic feed, search, trending"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from api.database import get_db
from api.templates import respond
from api.routes.auth import get_current_artist

router = APIRouter()


def compute_discovery_score(track: dict) -> float:
    import math
    from datetime import datetime
    plays = max(track.get("plays", 0), 1)
    likes = track.get("likes", 0)
    deposits = track.get("deposits", 0)
    created = track.get("created_at", "")
    like_ratio = min(likes / plays, 1.0)
    play_score = math.log10(plays + 1) / 5.0
    freshness = 0.5
    if created:
        try:
            created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            days_old = (datetime.now(created_dt.tzinfo) - created_dt).days
            freshness = max(0.0, 1.0 - (days_old / 30.0))
        except:
            pass
    deposit_score = min(deposits / 10.0, 1.0)
    return round(play_score * 0.30 + like_ratio * 0.25 + freshness * 0.20 + deposit_score * 0.10 + 0.15, 4)


@router.get("/")
async def discovery_feed(request: Request):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT t.*, a.username as artist_username, a.display_name as artist_name, a.genre as artist_genre FROM tracks t JOIN artists a ON t.artist_id=a.id ORDER BY t.created_at DESC LIMIT 50")
        tracks = [dict(r) for r in await cursor.fetchall()]
    finally:
        await db.close()
    for t in tracks:
        t["discovery_score"] = compute_discovery_score(t)
    tracks.sort(key=lambda x: x["discovery_score"], reverse=True)
    return respond("track/feed.html", {"request": request, "tracks": tracks, "feed_type": "discovery", "current_artist": await get_current_artist(request)})


@router.get("/trending")
async def trending(request: Request):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT t.*, a.username as artist_username, a.display_name as artist_name FROM tracks t JOIN artists a ON t.artist_id=a.id ORDER BY t.plays DESC LIMIT 30")
        tracks = [dict(r) for r in await cursor.fetchall()]
    finally:
        await db.close()
    return respond("track/feed.html", {"request": request, "tracks": tracks, "feed_type": "trending", "current_artist": await get_current_artist(request)})


@router.get("/new")
async def new_releases(request: Request):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT t.*, a.username as artist_username, a.display_name as artist_name FROM tracks t JOIN artists a ON t.artist_id=a.id ORDER BY t.created_at DESC LIMIT 30")
        tracks = [dict(r) for r in await cursor.fetchall()]
    finally:
        await db.close()
    return respond("track/feed.html", {"request": request, "tracks": tracks, "feed_type": "new", "current_artist": await get_current_artist(request)})


@router.get("/search")
async def search_page(request: Request):
    """Search with platform tabs."""
    q = request.query_params.get("q", "").strip()
    platform = request.query_params.get("platform", "all").lower()
    tracks = []
    semantic_results = []

    # Simple counts — total only, no platform breakdown to avoid errors
    counts = {"all": 0, "youtube": 0, "spotify": 0, "soundcloud": 0, "bandcamp": 0}

    try:
        db = await get_db()
        try:
            # Get total count
            cursor = await db.execute("SELECT COUNT(*) FROM tracks")
            counts["all"] = (await cursor.fetchone())[0]

            # Search tracks
            if q and len(q) >= 2:
                query = "SELECT t.*, a.username as artist_username, a.display_name as artist_name FROM tracks t JOIN artists a ON t.artist_id=a.id WHERE 1=1"
                params = []

                # Platform filter
                if platform == "youtube":
                    query += " AND (t.audio_url IS NOT NULL AND (t.audio_url LIKE '%youtube%' OR t.audio_url LIKE '%youtu.be%'))"
                elif platform == "spotify":
                    query += " AND (t.audio_url IS NOT NULL AND t.audio_url LIKE '%spotify%')"
                elif platform == "soundcloud":
                    query += " AND (t.audio_url IS NOT NULL AND t.audio_url LIKE '%soundcloud%')"
                elif platform == "bandcamp":
                    query += " AND (t.audio_url IS NOT NULL AND t.audio_url LIKE '%bandcamp%')"

                # Text search
                search_term = f"%{q}%"
                query += " AND (t.title LIKE ? OR t.genre LIKE ? OR a.display_name LIKE ? OR t.description LIKE ?)"
                params.extend([search_term] * 4)
                query += " ORDER BY t.plays DESC LIMIT 50"

                cursor = await db.execute(query, params)
                tracks = [dict(r) for r in await cursor.fetchall()]
            else:
                # No search query — show all tracks
                cursor = await db.execute("SELECT t.*, a.username as artist_username, a.display_name as artist_name FROM tracks t JOIN artists a ON t.artist_id=a.id ORDER BY t.plays DESC LIMIT 50")
                tracks = [dict(r) for r in await cursor.fetchall()]
        finally:
            await db.close()
    except Exception as e:
        # If DB query fails, return empty results
        import traceback
        traceback.print_exc()
        tracks = []

    try:
        current_artist = await get_current_artist(request)
    except:
        current_artist = None

    return respond("search.html", {
        "request": request, "query": q, "platform": platform,
        "tracks": tracks, "semantic_results": semantic_results,
        "counts": counts, "current_artist": current_artist,
    })


@router.get("/genre/{genre}")
async def by_genre(request: Request, genre: str):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT t.*, a.username as artist_username, a.display_name as artist_name FROM tracks t JOIN artists a ON t.artist_id=a.id WHERE t.genre LIKE ? ORDER BY t.plays DESC LIMIT 30", (f"%{genre}%",))
        tracks = [dict(r) for r in await cursor.fetchall()]
    finally:
        await db.close()
    return respond("track/feed.html", {"request": request, "tracks": tracks, "feed_type": "genre", "genre": genre, "current_artist": await get_current_artist(request)})
