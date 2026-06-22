"""API routes — Graph, Vectors, Semantic Search, Artist Profiles."""
import json
from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import JSONResponse
from api.database import get_db
from api.templates import respond
from api.vectors import search_service, graph_builder
from api.routes.auth import get_current_artist

router = APIRouter()


# ============================================================
# GRAPH API
# ============================================================

@router.get("/api/graph/data")
async def graph_data():
    """Get graph data for D3.js visualization."""
    db = await get_db()
    try:
        # Get all artists
        cursor = await db.execute(
            "SELECT id, username, display_name, genre, total_plays, total_earnings_cents FROM artists"
        )
        artists = [dict(r) for r in await cursor.fetchall()]

        # Build nodes
        nodes = []
        for a in artists:
            nodes.append({
                "id": a["id"],
                "username": a["username"],
                "name": a["display_name"] or a["username"],
                "genre": a["genre"] or "unknown",
                "plays": a["total_plays"] or 0,
                "earnings": (a["total_earnings_cents"] or 0) / 100,
            })

        # Build edges from follows
        edges = []
        seen = set()
        cursor = await db.execute("SELECT follower_id, followed_id FROM follows")
        for r in cursor.fetchall():
            key = (r["follower_id"], r["followed_id"])
            if key not in seen:
                edges.append({"source": r["follower_id"], "target": r["followed_id"], "type": "follow"})
                seen.add(key)

        # Build edges from genre similarity
        genre_groups = {}
        for a in artists:
            g = (a["genre"] or "unknown").lower()
            genre_groups.setdefault(g, []).append(a["id"])
        for g, ids in genre_groups.items():
            for i in range(len(ids)):
                for j in range(i+1, len(ids)):
                    edges.append({"source": ids[i], "target": ids[j], "type": "genre"})

        return JSONResponse({"nodes": nodes, "edges": edges})
    finally:
        await db.close()


@router.post("/api/graph/rebuild")
async def rebuild_graph():
    """Rebuild graph edges and compute layout. Admin/cron only."""
    db = await get_db()
    try:
        await graph_builder.generate_edges(db)
        graph = await graph_builder.compute_graph_layout(db)
        return JSONResponse({"status": "ok", "nodes": len(graph["nodes"]), "edges": len(graph["links"])})
    finally:
        await db.close()


# ============================================================
# SEMANTIC SEARCH API
# ============================================================

@router.get("/api/search/semantic")
async def semantic_search(q: str = "", limit: int = 20):
    """Semantic search for tracks."""
    if not q or len(q.strip()) < 2:
        return JSONResponse({"results": [], "query": q})

    db = await get_db()
    try:
        results = await search_service.search_tracks(q, db, limit)
        return JSONResponse({"results": results, "query": q})
    finally:
        await db.close()


@router.get("/api/artists/{artist_id}/similar")
async def similar_artists(artist_id: int, limit: int = 10):
    """Find artists similar to the given artist."""
    db = await get_db()
    try:
        results = await search_service.find_similar_artists(artist_id, db, limit)
        return JSONResponse({"results": results})
    finally:
        await db.close()


# ============================================================
# VECTOR MANAGEMENT
# ============================================================

@router.post("/api/vectors/embed/artist/{artist_id}")
async def embed_artist(artist_id: int):
    """Generate and store embedding for an artist."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM artists WHERE id=?", (artist_id,))
        artist = await cursor.fetchone()
        if not artist:
            raise HTTPException(status_code=404, detail="Artist not found")

        artist = dict(artist)
        embedding = await search_service.embed_artist(artist, db)

        # Store profile embedding
        await db.execute(
            "UPDATE artists SET profile_embedding=?, profile_embedding_updated=CURRENT_TIMESTAMP WHERE id=?",
            (embedding, artist_id)
        )

        # Compress full collection
        collection_vec = await search_service.compress_artist_collection(artist_id, db)
        await db.execute(
            "INSERT OR REPLACE INTO artist_collection_vectors (artist_id, collection_vector, updated_at) VALUES (?,?,CURRENT_TIMESTAMP)",
            (artist_id, collection_vec)
        )

        await db.commit()
        return JSONResponse({"status": "ok", "artist_id": artist_id})
    finally:
        await db.close()


@router.post("/api/vectors/embed/track/{track_id}")
async def embed_track(track_id: int):
    """Generate and store embedding for a track."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM tracks WHERE id=?", (track_id,))
        track = await cursor.fetchone()
        if not track:
            raise HTTPException(status_code=404, detail="Track not found")

        track = dict(track)
        embedding = await search_service.embed_track(track)

        await db.execute(
            "INSERT OR REPLACE INTO track_embeddings (track_id, embedding) VALUES (?,?)",
            (track_id, embedding)
        )
        await db.commit()
        return JSONResponse({"status": "ok", "track_id": track_id})
    finally:
        await db.close()


@router.post("/api/vectors/embed/all")
async def embed_all():
    """Embed all artists and tracks. Admin/cron only."""
    db = await get_db()
    try:
        # Embed all tracks
        cursor = await db.execute("SELECT id FROM tracks WHERE is_published=1")
        tracks = await cursor.fetchall()
        for t in tracks:
            await embed_track(t["id"])

        # Embed all artists
        cursor = await db.execute("SELECT id FROM artists")
        artists = await cursor.fetchall()
        for a in artists:
            await embed_artist(a["id"])

        return JSONResponse({"status": "ok", "tracks": len(tracks), "artists": len(artists)})
    finally:
        await db.close()


# ============================================================
# ARTIST PROFILE — Multi-Platform
# ============================================================

@router.get("/artists/{username}/edit")
async def edit_profile_page(request: Request, username: str):
    """Artist profile edit page."""
    current = await get_current_artist(request)
    if not current or current["username"] != username:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/auth/login")

    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM artists WHERE username=?", (username,))
        artist = await cursor.fetchone()
        if not artist:
            raise HTTPException(status_code=404, detail="Artist not found")

        cursor = await db.execute(
            "SELECT * FROM artist_platform_links WHERE artist_id=?",
            (artist["id"],)
        )
        platforms = {p["platform"]: dict(p) for p in await cursor.fetchall()}
    finally:
        await db.close()

    return respond("artist/profile_edit.html", {
        "request": request,
        "artist": dict(artist),
        "platforms": platforms,
        "current_artist": current,
    })


@router.post("/artists/{username}/edit")
async def save_profile(request: Request, username: str):
    """Save artist profile with platform links."""
    current = await get_current_artist(request)
    if not current or current["username"] != username:
        raise HTTPException(status_code=401, detail="Unauthorized")

    form = await request.form()

    db = await get_db()
    try:
        # Update artist profile
        await db.execute(
            "UPDATE artists SET "
            "display_name=?, bio=?, genre=?, location=?, "
            "website_url=?, soundcloud_url=?, bandcamp_url=?, "
            "instagram_url=?, twitter_url=?, tiktok_url=? "
            "WHERE id=?",
            (
                form.get("display_name", "").strip(),
                form.get("bio", "").strip(),
                form.get("genre", "").strip(),
                form.get("location", "").strip(),
                form.get("website_url", "").strip(),
                form.get("soundcloud_url", "").strip(),
                form.get("bandcamp_url", "").strip(),
                form.get("instagram_url", "").strip(),
                form.get("twitter_url", "").strip(),
                form.get("tiktok_url", "").strip(),
                current["id"],
            )
        )

        # Update platform links
        platform_links = [
            ("youtube", "youtube_url"),
            ("spotify", "spotify_url"),
            ("apple_music", "apple_music_url"),
            ("soundcloud", "soundcloud_url"),
            ("bandcamp", "bandcamp_url"),
            ("tidal", "tidal_url"),
            ("amazon_music", "amazon_music_url"),
        ]

        for platform, field_name in platform_links:
            url = form.get(field_name, "").strip()
            if url:
                await db.execute(
                    "INSERT OR REPLACE INTO artist_platform_links (artist_id, platform, url) VALUES (?,?,?)",
                    (current["id"], platform, url)
                )

        await db.commit()

        # Regenerate embeddings
        await embed_artist(current["id"])
    finally:
        await db.close()

    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=f"/artists/{username}?updated=1", status_code=303)


# ============================================================
# SEMANTIC SEARCH PAGE
# ============================================================

@router.get("/search")
async def search_page(request: Request):
    """Semantic search page."""
    query = request.query_params.get("q", "")
    results = []

    if query and len(query.strip()) >= 2:
        db = await get_db()
        try:
            results = await search_service.search_tracks(query, db, 20)
        finally:
            await db.close()

    current_artist = await get_current_artist(request)
    return respond("search.html", {
        "request": request,
        "query": query,
        "results": results,
        "current_artist": current_artist,
    })
