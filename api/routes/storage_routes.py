"""Storage tier and cloud provider routes."""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from api.database import get_db
from api.templates import respond
from api.routes.auth import get_current_artist
from api.storage_tiers import (
    STORAGE_TIERS, CLOUD_STORAGE_PROVIDERS, FREE_CLOUD_STORAGE,
    MUSIC_SPECIFIC_STORAGE, RECOMMENDED_SETUPS, calculator,
    upgrade_flow, calculate_2026_costs
)

router = APIRouter()


@router.get("/storage")
async def storage_page(request: Request):
    """Storage tiers and settings page."""
    artist = await get_current_artist(request)
    if not artist:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/auth/login")

    db = await get_db()
    try:
        # Get current usage
        cursor = await db.execute(
            "SELECT COUNT(*) FROM tracks WHERE artist_id=?", (artist["id"],)
        )
        current_tracks = (await cursor.fetchone())[0]

        # Get tier info
        tier = artist.get("tier", "free")
        tier_info = STORAGE_TIERS.get(tier, STORAGE_TIERS["free"])

        # Calculate usage
        max_tracks = tier_info["max_tracks"]
        storage_gb = tier_info["storage_gb"] if tier_info["storage_gb"] > 0 else 99999
        used_gb = (current_tracks * 7.2) / 1024  # Estimate: 7.2MB per track
        usage_pct = min(100, (current_tracks / max_tracks * 100) if max_tracks > 0 else 0)

        # Get connected providers
        cursor = await db.execute(
            "SELECT platform FROM artist_platform_links WHERE artist_id=?",
            (artist["id"],)
        )
        connected = [r["platform"] for r in await cursor.fetchall()]
    finally:
        await db.close()

    return respond("storage.html", {
        "request": request,
        "artist": artist,
        "tiers": STORAGE_TIERS,
        "providers": CLOUD_STORAGE_PROVIDERS,
        "free_storage": FREE_CLOUD_STORAGE,
        "music_storage": MUSIC_SPECIFIC_STORAGE,
        "recommended_setups": RECOMMENDED_SETUPS,
        "current_tier": tier,
        "tier_name": tier_info["name"],
        "current_tracks": current_tracks,
        "max_tracks": max_tracks,
        "used_gb": round(used_gb, 2),
        "total_gb": storage_gb,
        "usage_pct": round(usage_pct, 1),
        "connected_providers": connected,
        "current_artist": artist,
    })


@router.post("/api/storage/calculate")
async def calculate_storage(request: Request):
    """Calculate storage needs via API."""
    form = await request.form()
    tracks = int(form.get("tracks", 100))
    duration = float(form.get("duration", 3.5))
    quality = form.get("quality", "mp3_320")

    needs = calculator.calculate_needs(tracks, duration, quality)
    costs = calculator.calculate_costs(needs["total_audio_gb"])
    recommendation = calculator.recommend_tier(tracks, needs["total_audio_gb"])

    return JSONResponse({
        "needs": needs,
        "costs": costs,
        "recommendation": recommendation,
    })
