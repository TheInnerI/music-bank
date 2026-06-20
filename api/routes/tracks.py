"""Track routes — listing, detail, play, like"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from api.database import get_db
from api.templates import respond
from api.routes.auth import get_current_artist

router = APIRouter()


@router.get("/{track_id}")
async def track_detail(request: Request, track_id: int):
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT t.*, a.username as artist_username, a.display_name as artist_name FROM tracks t JOIN artists a ON t.artist_id=a.id WHERE t.id=?",
            (track_id,)
        )
        track = await cursor.fetchone()
        if not track:
            raise HTTPException(status_code=404, detail="Track not found")
        track = dict(track)

        # Get more tracks by same artist
        cursor = await db.execute(
            "SELECT id, title, plays FROM tracks WHERE artist_id=? AND id!=? ORDER BY plays DESC LIMIT 5",
            (track["artist_id"], track_id)
        )
        more_tracks = [dict(r) for r in await cursor.fetchall()]
    finally:
        await db.close()

    current_artist = await get_current_artist(request)
    liked = False
    if current_artist:
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT 1 FROM likes WHERE track_id=? AND artist_id=?",
                (track_id, current_artist["id"])
            )
            liked = await cursor.fetchone() is not None
        finally:
            await db.close()

# Get artist's wallet address for crypto deposits
        cursor = await db.execute(
            "SELECT base_wallet_address, eth_wallet_address FROM artists WHERE id=?",
            (track["artist_id"],)
        )
        artist_row = await cursor.fetchone()
        artist_wallet = None
        if artist_row:
            artist_wallet = artist_row["base_wallet_address"] or artist_row["eth_wallet_address"]

    return respond("track/detail.html", {
        "request": request,
        "track": track,
        "more_tracks": more_tracks,
        "liked": liked,
        "current_artist": current_artist,
        "artist_wallet": artist_wallet,
    })


@router.post("/{track_id}/play")
async def record_play(request: Request, track_id: int):
    """Record a play event."""
    form = await request.form()
    duration = int(form.get("duration", 0) or 0)
    source = form.get("source", "direct")

    current_artist = await get_current_artist(request)
    listener_id = current_artist["id"] if current_artist else None

    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO plays (track_id, listener_id, duration_listened, source) VALUES (?,?,?,?)",
            (track_id, listener_id, duration, source)
        )
        await db.execute("UPDATE tracks SET plays = plays + 1 WHERE id=?", (track_id,))
        # Update artist total plays
        await db.execute(
            "UPDATE artists SET total_plays = total_plays + 1 WHERE id=(SELECT artist_id FROM tracks WHERE id=?)",
            (track_id,)
        )
        await db.commit()
    finally:
        await db.close()

    return JSONResponse({"status": "ok"})


@router.post("/{track_id}/like")
async def toggle_like(request: Request, track_id: int):
    """Toggle like on a track."""
    current_artist = await get_current_artist(request)
    if not current_artist:
        raise HTTPException(status_code=401, detail="Must be logged in to like")

    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT 1 FROM likes WHERE track_id=? AND artist_id=?",
            (track_id, current_artist["id"])
        )
        existing = await cursor.fetchone()

        if existing:
            await db.execute(
                "DELETE FROM likes WHERE track_id=? AND artist_id=?",
                (track_id, current_artist["id"])
            )
            await db.execute("UPDATE tracks SET likes = likes - 1 WHERE id=?", (track_id,))
            liked = False
        else:
            await db.execute(
                "INSERT INTO likes (track_id, artist_id) VALUES (?,?)",
                (track_id, current_artist["id"])
            )
            await db.execute("UPDATE tracks SET likes = likes + 1 WHERE id=?", (track_id,))
            liked = True

        await db.commit()

        cursor = await db.execute("SELECT likes FROM tracks WHERE id=?", (track_id,))
        count = (await cursor.fetchone())[0]
    finally:
        await db.close()

    return JSONResponse({"liked": liked, "count": count})
