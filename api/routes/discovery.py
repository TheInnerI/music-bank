"""Discovery routes — algorithmic feed, search, trending"""
from fastapi import APIRouter, Request
from api.database import get_db
from api.templates import respond
from api.routes.auth import get_current_artist

# Optional: TurboVec semantic search
search_service = None
try:
    from api.vectors import search_service
except Exception as e:
    print(f"[Discovery] TurboVec not available: {e}")

router = APIRouter()


@router.post("/api/search/index")
async def index_search(request: Request):
    """Index all tracks for semantic search."""
    if not search_service:
        return {"status": "error", "message": "TurboVec not available"}
    current_artist = await get_current_artist(request)
    if not current_artist:
        return {"status": "error", "message": "Must be logged in"}
    db = await get_db()
    try:
        count = await search_service.index_tracks(db)
        return {"status": "ok", "message": f"Indexed {count} tracks", "count": count}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        await db.close()


@router.get("/search")
async def search_page(request: Request):
    """Search with platform tabs + optional TurboVec semantic search."""
    q = request.query_params.get("q", "").strip()
    platform = request.query_params.get("platform", "all").lower()
    tracks = []
    counts = {"all": 0, "youtube": 0, "spotify": 0, "soundcloud": 0, "bandcamp": 0}

    try:
        db = await get_db()
        try:
            # Get all tracks
            cursor = await db.execute(
                "SELECT t.id, t.title, t.plays, t.genre, t.audio_url, "
                "a.username as artist_username, a.display_name as artist_name "
                "FROM tracks t JOIN artists a ON t.artist_id=a.id "
                "ORDER BY t.plays DESC LIMIT 50"
            )
            all_tracks = [dict(r) for r in await cursor.fetchall()]
            counts["all"] = len(all_tracks)

            # Try semantic search if we have a query and search_service is available
            if q and len(q) >= 2 and search_service:
                try:
                    if not search_service._track_embeddings:
                        await search_service.index_tracks(db)
                    semantic_results = await search_service.search_tracks(q, db, 20)
                    if platform and platform != "all":
                        semantic_results = [r for r in semantic_results if r.get("audio_url") and platform in r["audio_url"].lower()]
                    if semantic_results:
                        tracks = semantic_results
                except Exception as e:
                    print(f"[Search] TurboVec error: {e}")

            # Fall back to text search if no semantic results
            if not tracks:
                q_lower = q.lower() if q else ""
                if q_lower:
                    tracks = [t for t in all_tracks if
                        q_lower in t["title"].lower() or
                        q_lower in (t["genre"] or "").lower() or
                        q_lower in t["artist_name"].lower()
                    ]
                else:
                    tracks = all_tracks

            # Filter by platform
            if platform and platform != "all":
                tracks = [t for t in tracks if t.get("audio_url") and platform in t["audio_url"].lower()]
        finally:
            await db.close()
    except Exception as e:
        import traceback
        print(f"[Search] Error: {traceback.format_exc()}")

    try:
        current_artist = await get_current_artist(request)
    except:
        current_artist = None

    return respond("search.html", {
        "request": request, "query": q, "platform": platform,
        "tracks": tracks, "semantic_results": [],
        "counts": counts, "current_artist": current_artist,
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
