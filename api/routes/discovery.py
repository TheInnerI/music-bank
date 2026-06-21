"""Discovery routes — algorithmic feed, search, trending"""
from fastapi import APIRouter, Request
from api.database import get_db
from api.templates import respond
from api.routes.auth import get_current_artist

router = APIRouter()


@router.get("/search")
async def search_page(request: Request):
    """Search with platform tabs."""
    q = request.query_params.get("q", "").strip()
    platform = request.query_params.get("platform", "all").lower()
    tracks = []
    counts = {"all": 0, "youtube": 0, "spotify": 0, "soundcloud": 0, "bandcamp": 0}

    db = await get_db()
    try:
        # Get all tracks (no filter)
        cursor = await db.execute(
            "SELECT t.id, t.title, t.plays, t.genre, t.audio_url, "
            "a.username as artist_username, a.display_name as artist_name "
            "FROM tracks t JOIN artists a ON t.artist_id=a.id "
            "ORDER BY t.plays DESC LIMIT 50"
        )
        all_tracks = [dict(r) for r in await cursor.fetchall()]
        counts["all"] = len(all_tracks)

        # Filter by search query if provided
        if q and len(q) >= 2:
            q_lower = q.lower()
            tracks = [t for t in all_tracks if
                q_lower in t["title"].lower() or
                q_lower in (t["genre"] or "").lower() or
                q_lower in t["artist_name"].lower()
            ]
        else:
            tracks = all_tracks

        # Filter by platform if not 'all'
        if platform and platform != "all":
            if platform == "youtube":
                tracks = [t for t in tracks if t["audio_url"] and ("youtube.com" in t["audio_url"] or "youtu.be" in t["audio_url"])]
            elif platform == "spotify":
                tracks = [t for t in tracks if t["audio_url"] and "spotify" in t["audio_url"]]
            elif platform == "soundcloud":
                tracks = [t for t in tracks if t["audio_url"] and "soundcloud" in t["audio_url"]]
            elif platform == "bandcamp":
                tracks = [t for t in tracks if t["audio_url"] and "bandcamp" in t["audio_url"]]

    finally:
        await db.close()

    current_artist = await get_current_artist(request)

    return respond("search.html", {
        "request": request,
        "query": q,
        "platform": platform,
        "tracks": tracks,
        "semantic_results": [],
        "counts": counts,
        "current_artist": current_artist,
    })


@router.get("/")
async def discovery_feed(request: Request):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT t.*, a.username as artist_username, a.display_name as artist_name FROM tracks t JOIN artists a ON t.artist_id=a.id ORDER BY t.created_at DESC LIMIT 50")
        tracks = [dict(r) for r in await cursor.fetchall()]
    finally:
        await db.close()
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


@router.get("/genre/{genre}")
async def by_genre(request: Request, genre: str):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT t.*, a.username as artist_username, a.display_name as artist_name FROM tracks t JOIN artists a ON t.artist_id=a.id WHERE t.genre LIKE ? ORDER BY t.plays DESC LIMIT 30", (f"%{genre}%",))
        tracks = [dict(r) for r in await cursor.fetchall()]
    finally:
        await db.close()
    return respond("track/feed.html", {"request": request, "tracks": tracks, "feed_type": "genre", "genre": genre, "current_artist": await get_current_artist(request)})
