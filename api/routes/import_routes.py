"""Import routes — Universal music import from all platforms."""
import json
from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import JSONResponse
from api.database import get_db
from api.templates import respond
from api.routes.auth import get_current_artist
from api.importer import universal_importer
from api.auto_protect import auto_protect_track

router = APIRouter()


# ============================================================
# IMPORT DASHBOARD
# ============================================================

@router.get("/import")
async def import_dashboard(request: Request):
    """Universal import dashboard."""
    artist = await get_current_artist(request)
    if not artist:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/auth/login")

    db = await get_db()
    try:
        # Get existing platform links
        cursor = await db.execute(
            "SELECT platform, url, platform_id, is_verified, follower_count "
            "FROM artist_platform_links WHERE artist_id=?",
            (artist["id"],)
        )
        platforms = {p["platform"]: dict(p) for p in await cursor.fetchall()}

        # Get import history
        cursor = await db.execute(
            "SELECT * FROM import_history WHERE artist_id=? ORDER BY created_at DESC LIMIT 20",
            (artist["id"],)
        )
        import_history = [dict(h) for h in await cursor.fetchall()]

        # Get track count
        cursor = await db.execute(
            "SELECT COUNT(*) FROM tracks WHERE artist_id=?", (artist["id"],)
        )
        track_count = (await cursor.fetchone())[0]
    finally:
        await db.close()

    return respond("import/dashboard.html", {
        "request": request,
        "artist": artist,
        "platforms": platforms,
        "import_history": import_history,
        "track_count": track_count,
        "current_artist": artist,
    })


# ============================================================
# YOUTUBE IMPORT
# ============================================================

@router.post("/import/youtube")
async def import_youtube(request: Request):
    """Import from YouTube."""
    artist = await get_current_artist(request)
    if not artist:
        raise HTTPException(status_code=401, detail="Must be logged in")

    form = await request.form()
    channel_id = form.get("channel_id", "").strip()
    username = form.get("username", "").strip()

    if not channel_id and not username:
        raise HTTPException(status_code=400, detail="Channel ID or username required")

    db = await get_db()
    try:
        # Get channel info
        channel = await universal_importer.youtube.get_channel_info(
            channel_id=channel_id, username=username
        )

        if not channel:
            raise HTTPException(status_code=404, detail="YouTube channel not found")

        # Save platform link
        await db.execute(
            "INSERT OR REPLACE INTO artist_platform_links "
            "(artist_id, platform, url, platform_id, is_verified, follower_count) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (artist["id"], "youtube", channel["url"], channel["platform_id"],
             1, channel.get("subscriber_count", 0))
        )

        # Get videos
        videos = await universal_importer.youtube.get_channel_videos(
            channel_id=channel.get("platform_id", ""),
            username=username,
        )

        # Import each video
        imported = 0
        for video in videos:
            try:
                # Check for duplicates
                cursor = await db.execute(
                    "SELECT id FROM tracks WHERE artist_id=? AND audio_url LIKE ?",
                    (artist["id"], f"%{video['platform_id']}%")
                )
                if await cursor.fetchone():
                    continue

                # Insert track
                await db.execute(
                    "INSERT INTO tracks "
                    "(artist_id, title, description, duration_seconds, audio_url, is_published) "
                    "VALUES (?, ?, ?, ?, ?, 1)",
                    (artist["id"], video["title"], video.get("description", ""),
                     video.get("duration", 0), video.get("url", ""))
                )

                # Get track ID
                cursor = await db.execute("SELECT last_insert_rowid()")
                track_id = (await cursor.fetchone())[0]

                # Store platform link
                await db.execute(
                    "INSERT OR REPLACE INTO artist_platform_links "
                    "(artist_id, platform, url, platform_id) VALUES (?, ?, ?, ?)",
                    (artist["id"], "youtube", video["url"], video["platform_id"])
                )

                imported += 1
            except Exception:
                continue

        # Log import
        await db.execute(
            "INSERT INTO import_history (artist_id, platform, items_imported, status) "
            "VALUES (?, ?, ?, ?)",
            (artist["id"], "youtube", imported, "completed")
        )

        await db.commit()

        return JSONResponse({
            "status": "ok",
            "platform": "youtube",
            "channel": channel["title"],
            "imported": imported,
            "total_found": len(videos),
            "message": f"Imported {imported} tracks from YouTube channel '{channel['title']}'",
        })
    finally:
        await db.close()


# ============================================================
# SPOTIFY IMPORT
# ============================================================

@router.post("/import/spotify")
async def import_spotify(request: Request):
    """Import from Spotify."""
    artist = await get_current_artist(request)
    if not artist:
        raise HTTPException(status_code=401, detail="Must be logged in")

    form = await request.form()
    spotify_artist_id = form.get("spotify_artist_id", "").strip()
    spotify_artist_name = form.get("spotify_artist_name", "").strip()

    if not spotify_artist_id and not spotify_artist_name:
        raise HTTPException(status_code=400, detail="Spotify artist ID or name required")

    db = await get_db()
    try:
        artist_info = await universal_importer.spotify.get_artist_info(
            artist_id=spotify_artist_id, artist_name=spotify_artist_name
        )

        if not artist_info:
            raise HTTPException(status_code=404, detail="Spotify artist not found")

        # Save platform link
        await db.execute(
            "INSERT OR REPLACE INTO artist_platform_links "
            "(artist_id, platform, url, platform_id, is_verified, follower_count) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (artist["id"], "spotify", artist_info["url"], artist_info["platform_id"],
             1, artist_info.get("followers", 0))
        )

        # Get tracks
        tracks = await universal_importer.spotify.get_artist_tracks(
            artist_id=artist_info.get("platform_id", ""),
            artist_name=spotify_artist_name,
        )

        imported = 0
        for track in tracks:
            try:
                cursor = await db.execute(
                    "SELECT id FROM tracks WHERE artist_id=? AND isrc=?",
                    (artist["id"], track.get("isrc", ""))
                )
                if await cursor.fetchone():
                    continue

                await db.execute(
                    "INSERT INTO tracks "
                    "(artist_id, title, description, duration_seconds, audio_url, is_published, isrc) "
                    "VALUES (?, ?, ?, ?, ?, 1, ?)",
                    (artist["id"], track["title"], f"From album: {track.get('album', '')}",
                     track.get("duration", 0), track.get("url", ""), track.get("isrc", ""))
                )
                imported += 1
            except Exception:
                continue

        await db.execute(
            "INSERT INTO import_history (artist_id, platform, items_imported, status) "
            "VALUES (?, ?, ?, ?)",
            (artist["id"], "spotify", imported, "completed")
        )

        await db.commit()

        return JSONResponse({
            "status": "ok",
            "platform": "spotify",
            "artist": artist_info["name"],
            "imported": imported,
            "message": f"Imported {imported} tracks from Spotify artist '{artist_info['name']}'",
        })
    finally:
        await db.close()


# ============================================================
# APPLE MUSIC IMPORT
# ============================================================

@router.post("/import/apple-music")
async def import_apple_music(request: Request):
    """Import from Apple Music."""
    artist = await get_current_artist(request)
    if not artist:
        raise HTTPException(status_code=401, detail="Must be logged in")

    form = await request.form()
    apple_artist_name = form.get("apple_artist_name", "").strip()

    if not apple_artist_name:
        raise HTTPException(status_code=400, detail="Apple Music artist name required")

    db = await get_db()
    try:
        artist_info = await universal_importer.apple_music.get_artist_info(
            artist_name=apple_artist_name
        )

        if not artist_info:
            raise HTTPException(status_code=404, detail="Apple Music artist not found")

        await db.execute(
            "INSERT OR REPLACE INTO artist_platform_links "
            "(artist_id, platform, url, platform_id, is_verified) "
            "VALUES (?, ?, ?, ?, ?)",
            (artist["id"], "apple_music", artist_info["url"], artist_info["platform_id"], 1)
        )

        tracks = await universal_importer.apple_music.get_artist_tracks(
            artist_id=artist_info.get("platform_id", ""),
            artist_name=apple_artist_name,
        )

        imported = 0
        for track in tracks:
            try:
                await db.execute(
                    "INSERT INTO tracks "
                    "(artist_id, title, description, duration_seconds, audio_url, is_published) "
                    "VALUES (?, ?, ?, ?, ?, 1)",
                    (artist["id"], track["title"], f"From album: {track.get('album', '')}",
                     track.get("duration", 0), track.get("url", ""))
                )
                imported += 1
            except Exception:
                continue

        await db.execute(
            "INSERT INTO import_history (artist_id, platform, items_imported, status) "
            "VALUES (?, ?, ?, ?)",
            (artist["id"], "apple_music", imported, "completed")
        )

        await db.commit()

        return JSONResponse({
            "status": "ok",
            "platform": "apple_music",
            "artist": artist_info["name"],
            "imported": imported,
            "message": f"Imported {imported} tracks from Apple Music artist '{artist_info['name']}'",
        })
    finally:
        await db.close()


# ============================================================
# DISTROKID MIGRATION
# ============================================================

@router.post("/import/distrokid")
async def import_distrokid(request: Request):
    """Import from DistroKid CSV export."""
    artist = await get_current_artist(request)
    if not artist:
        raise HTTPException(status_code=401, detail="Must be logged in")

    form = await request.form()
    csv_content = form.get("csv_content", "").strip()

    if not csv_content:
        raise HTTPException(status_code=400, detail="CSV content required")

    db = await get_db()
    try:
        releases = await universal_importer.distrokid.parse_distrokid_csv(csv_content)

        imported = 0
        for release in releases:
            try:
                await db.execute(
                    "INSERT INTO tracks "
                    "(artist_id, title, description, audio_url, is_published, isrc, upc) "
                    "VALUES (?, ?, ?, ?, 1, ?, ?)",
                    (artist["id"], release["title"], f"From DistroKid: {release.get('album', '')}",
                     release.get("stores", {}).get("spotify", ""),
                     release.get("isrc", ""), release.get("upc", ""))
                )
                imported += 1
            except Exception:
                continue

        await db.execute(
            "INSERT INTO import_history (artist_id, platform, items_imported, status) "
            "VALUES (?, ?, ?, ?)",
            (artist["id"], "distrokid", imported, "completed")
        )

        await db.commit()

        return JSONResponse({
            "status": "ok",
            "platform": "distrokid",
            "imported": imported,
            "message": f"Imported {imported} releases from DistroKid",
        })
    finally:
        await db.close()


# ============================================================
# UNIVERSAL IMPORT (ALL PLATFORMS)
# ============================================================

@router.post("/import/all")
async def import_all_platforms(request: Request):
    """Import from all connected platforms at once."""
    artist = await get_current_artist(request)
    if not artist:
        raise HTTPException(status_code=401, detail="Must be logged in")

    form = await request.form()

    platforms = {}
    if form.get("youtube_channel") or form.get("youtube_username"):
        platforms["youtube"] = {
            "channel_id": form.get("youtube_channel", ""),
            "username": form.get("youtube_username", ""),
        }
    if form.get("spotify_artist_id") or form.get("spotify_artist_name"):
        platforms["spotify"] = {
            "artist_id": form.get("spotify_artist_id", ""),
            "artist_name": form.get("spotify_artist_name", ""),
        }
    if form.get("apple_artist_name"):
        platforms["apple_music"] = {
            "artist_name": form.get("apple_artist_name", ""),
        }

    if not platforms:
        raise HTTPException(status_code=400, detail="No platforms specified")

    db = await get_db()
    try:
        results = await universal_importer.import_all(
            artist_id=artist["id"],
            platforms=platforms,
            db=db,
        )
        return JSONResponse({"status": "ok", **results})
    finally:
        await db.close()
