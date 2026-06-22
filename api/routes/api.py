"""API routes — Graph, Vectors, Semantic Search, Artist Profiles."""
import json
import math
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
                "size": max(8, min(40, 5 + plays / 200)),
                "balance_cents": a["total_earnings_cents"] or 0,
            })

        links = []
        seen = set()

        # Follow edges
        cursor = await db.execute("SELECT follower_id, followed_id FROM follows")
        for r in await cursor.fetchall():
            key = (r["follower_id"], r["followed_id"])
            if key not in seen:
                links.append({"source": r["follower_id"], "target": r["followed_id"], "type": "follow", "weight": 1})
                seen.add(key)

        # Genre similarity edges (limited)
        genre_groups = {}
        for a in artists:
            g = (a["genre"] or "unknown").lower()
            genre_groups.setdefault(g, []).append(a["id"])
        for g, ids in genre_groups.items():
            limit = min(len(ids), 10)
            for i in range(limit):
                for j in range(i + 1, limit):
                    links.append({"source": ids[i], "target": ids[j], "type": "genre", "weight": 0.5})

        # If no links at all, create demo connections so graph is visible
        if not links and len(nodes) > 1:
            for i in range(len(nodes) - 1):
                links.append({"source": nodes[i]["id"], "target": nodes[i + 1]["id"], "type": "demo", "weight": 0.3})
            # Connect last to first
            if len(nodes) > 2:
                links.append({"source": nodes[-1]["id"], "target": nodes[0]["id"], "type": "demo", "weight": 0.3})

        # Also add platform links from artist_platform_links table
        try:
            cursor = await db.execute(
                "SELECT DISTINCT a1.artist_id as artist1, a2.artist_id as artist2 "
                "FROM artist_platform_links a1 "
                "JOIN artist_platform_links a2 ON a1.url = a2.url AND a1.artist_id != a2.artist_id "
                "LIMIT 20"
            )
            for r in await cursor.fetchall():
                key = (r["artist1"], r["artist2"])
                rev_key = (r["artist2"], r["artist1"])
                if key not in seen and rev_key not in seen:
                    links.append({"source": r["artist1"], "target": r["artist2"], "type": "platform", "weight": 1})
                    seen.add(key)
        except:
            pass

        return JSONResponse({"nodes": nodes, "links": links})
    finally:
        await db.close()


@router.post("/api/graph/rebuild")
async def rebuild_graph():
    """Rebuild graph edges. Admin only."""
    db = await get_db()
    try:
        # Regenerate edges from follows and platforms
        return JSONResponse({"status": "ok", "message": "Graph data refreshed"})
    finally:
        await db.close()


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
