"""Artist routes — profiles, dashboard, upload"""
import bcrypt
from fastapi import APIRouter, Request, HTTPException
from api.database import get_db
from api.templates import respond
from api.routes.auth import get_current_artist

router = APIRouter()


@router.get("/dashboard")
async def dashboard(request: Request):
    artist = await get_current_artist(request)
    if not artist:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/auth/login")

    db = await get_db()
    try:
        # Get artist's tracks
        cursor = await db.execute(
            "SELECT * FROM tracks WHERE artist_id=? ORDER BY created_at DESC",
            (artist["id"],)
        )
        tracks = [dict(r) for r in await cursor.fetchall()]

        # Get recent transactions
        cursor = await db.execute(
            "SELECT * FROM bank_transactions WHERE artist_id=? ORDER BY created_at DESC LIMIT 10",
            (artist["id"],)
        )
        transactions = [dict(r) for r in await cursor.fetchall()]

        # Get followers count
        cursor = await db.execute("SELECT COUNT(*) FROM follows WHERE followed_id=?", (artist["id"],))
        followers = (await cursor.fetchone())[0]

        # Get YouTube channel info if linked
        youtube_stats = None
        cursor = await db.execute(
            "SELECT url, platform_id FROM artist_platform_links WHERE artist_id=? AND platform='youtube'",
            (artist["id"],)
        )
        yt_link = await cursor.fetchone()
        if yt_link:
            # Extract channel ID from URL
            yt_url = yt_link["url"]
            channel_id = yt_link["platform_id"]
            if not channel_id and "channel/" in yt_url:
                channel_id = yt_url.split("channel/")[1].split("/")[0].split("?")[0]
            youtube_stats = {
                "channel_id": channel_id,
                "url": yt_url,
                "platform_id": yt_link["platform_id"],
            }

        # Get lifetime earnings
        cursor = await db.execute(
            "SELECT COALESCE(SUM(amount_cents),0) as total FROM earnings_ledger WHERE artist_id=?",
            (artist["id"],)
        )
        lifetime_earnings = (await cursor.fetchone())["total"]
    finally:
        await db.close()

    return respond("artist/dashboard.html", {
        "request": request,
        "artist": artist,
        "tracks": tracks,
        "transactions": transactions,
        "followers": followers,
        "youtube_stats": youtube_stats,
        "lifetime_earnings": lifetime_earnings,
    })


@router.get("/{username}")
async def profile(request: Request, username: str):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM artists WHERE username=?", (username,))
        artist = await cursor.fetchone()
        if not artist:
            raise HTTPException(status_code=404, detail="Artist not found")
        artist = dict(artist)

        cursor = await db.execute(
            "SELECT * FROM tracks WHERE artist_id=? AND is_published=1 ORDER BY plays DESC",
            (artist["id"],)
        )
        tracks = [dict(r) for r in await cursor.fetchall()]

        cursor = await db.execute("SELECT COUNT(*) FROM follows WHERE followed_id=?", (artist["id"],))
        followers = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM follows WHERE follower_id=?", (artist["id"],))
        following = (await cursor.fetchone())[0]
    finally:
        await db.close()

    current_artist = await get_current_artist(request)
    is_following = False
    if current_artist and current_artist["id"] != artist["id"]:
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT 1 FROM follows WHERE follower_id=? AND followed_id=?",
                (current_artist["id"], artist["id"])
            )
            is_following = await cursor.fetchone() is not None
        finally:
            await db.close()

    return respond("artist/profile.html", {
        "request": request,
        "artist": artist,
        "tracks": tracks,
        "followers": followers,
        "following": following,
        "is_following": is_following,
        "current_artist": current_artist,
    })


@router.get("/upload")
async def upload_page(request: Request):
    artist = await get_current_artist(request)
    if not artist:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/auth/login")
    return respond("artist/upload.html", {"request": request, "artist": artist, "error": None, "success": None})


@router.post("/upload")
async def upload_track(request: Request):
    artist = await get_current_artist(request)
    if not artist:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/auth/login")

    form = await request.form()
    title = form.get("title", "").strip()
    description = form.get("description", "").strip()
    genre = form.get("genre", "").strip()
    bpm = int(form.get("bpm", 0) or 0)
    key_signature = form.get("key_signature", "").strip()
    mood = form.get("mood", "").strip()
    lyrics = form.get("lyrics", "").strip()

    if not title:
        return respond("artist/upload.html", {"request": request, "artist": artist, "error": "Title is required", "success": None})

    # In MVP, audio_url is a placeholder. In production, this handles file upload.
    audio_url = f"/static/audio/{title.lower().replace(' ', '_')}.mp3"

    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO tracks (artist_id, title, description, genre, audio_url, bpm, key_signature, mood, lyrics, is_published) VALUES (?,?,?,?,?,?,?,?,?,1)",
            (artist["id"], title, description, genre, audio_url, bpm, key_signature, mood, lyrics)
        )
        await db.commit()
    finally:
        await db.close()

    return respond("artist/upload.html", {"request": request, "artist": artist, "error": None, "success": f"'{title}' uploaded successfully!"})
