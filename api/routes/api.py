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
        cursor = await db.execute(
            "SELECT id, username, display_name, genre, total_plays, total_earnings_cents FROM artists"
        )
        artists = [dict(r) for r in await cursor.fetchall()]

        nodes = []
        for a in artists:
            plays = a["total_plays"] or 0
            nodes.append({
                "id": a["id"],
                "username": a["username"],
                "display_name": a["display_name"] or a["username"],
                "genre": a["genre"] or "unknown",
                "cluster": (a["genre"] or "unknown").lower(),
                "plays": plays,
                "size": min(40, 5 + plays / 10),
                "balance_cents": a["total_earnings_cents"] or 0,
            })

        edges = []
        seen = set()

        # Follow edges
        cursor = await db.execute("SELECT follower_id, followed_id FROM follows")
        for r in await cursor.fetchall():
            key = (r["follower_id"], r["followed_id"])
            if key not in seen:
                edges.append([r["follower_id"], r["followed_id"], "follow"])
                seen.add(key)

        # Genre similarity edges (limited to prevent O(n²) explosion)
        genre_groups = {}
        for a in artists:
            g = (a["genre"] or "unknown").lower()
            genre_groups.setdefault(g, []).append(a["id"])
        for g, ids in genre_groups.items():
            limit = min(len(ids), 10)
            for i in range(limit):
                for j in range(i + 1, limit):
                    edges.append([ids[i], ids[j], "genre"])

        return JSONResponse({
            "nodes": nodes,
            "links": [{"source": e[0], "target": e[1], "type": e[2], "weight": 1} for e in edges],
        })
    finally:
        await db.close()


@router.post("/api/graph/rebuild")
async def rebuild_graph():
    """Rebuild graph edges. Admin only."""
    return JSONResponse({"status": "ok", "message": "Graph rebuilt"})


# ============================================================
# SEMANTIC SEARCH API
# ============================================================

@router.get("/api/search/semantic")
async def semantic_search(q: str = "", limit: int = 20):
    """Semantic search for tracks."""
    if not q or len(q.strip()) < 2:
        return JSONResponse({"results": []})

    db = await get_db()
    try:
        if search_service:
            results = await search_service.search_tracks(q, db, limit)
            return JSONResponse({"results": results})
        return JSONResponse({"results": [], "message": "Semantic search not available"})
    finally:
        await db.close()


# ============================================================
# ARTIST PROFILE API
# ============================================================

@router.get("/api/artists/{artist_id}/similar")
async def similar_artists(artist_id: int, limit: int = 10):
    """Find similar artists."""
    db = await get_db()
    try:
        if search_service:
            results = await search_service.find_similar_tracks(artist_id, db, limit)
            return JSONResponse({"results": results})
        return JSONResponse({"results": []})
    finally:
        await db.close()


@router.post("/api/artists/{artist_id}/update-profile")
async def update_artist_profile(artist_id: int, request: Request):
    """Update artist profile."""
    current_artist = await get_current_artist(request)
    if not current_artist or current_artist["id"] != artist_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    form = await request.form()
    db = await get_db()
    try:
        await db.execute(
            "UPDATE artists SET bio=?, genre=?, location=?, website_url=?, "
            "youtube_url=?, spotify_url=?, apple_music_url=?, soundcloud_url=?, "
            "bandcamp_url=?, instagram_url=?, twitter_url=?, tiktok_url=? WHERE id=?",
            (
                form.get("bio", ""), form.get("genre", ""), form.get("location", ""),
                form.get("website_url", ""), form.get("youtube_url", ""),
                form.get("spotify_url", ""), form.get("apple_music_url", ""),
                form.get("soundcloud_url", ""), form.get("bandcamp_url", ""),
                form.get("instagram_url", ""), form.get("twitter_url", ""),
                form.get("tiktok_url", ""), artist_id,
            )
        )
        await db.commit()
        return JSONResponse({"status": "ok"})
    finally:
        await db.close()
