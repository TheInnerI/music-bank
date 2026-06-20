"""Tier upgrade routes."""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from api.database import get_db
from api.templates import respond
from api.routes.auth import get_current_artist
from api.storage_tiers import STORAGE_TIERS

router = APIRouter()


@router.get("/upgrade")
async def upgrade_page(request: Request):
    """Tier upgrade page."""
    artist = await get_current_artist(request)
    if not artist:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/auth/login")

    current_tier = artist.get("tier", "free")

    return respond("upgrade.html", {
        "request": request,
        "artist": artist,
        "tiers": STORAGE_TIERS,
        "current_tier": current_tier,
    })


@router.post("/api/upgrade")
async def upgrade_tier(request: Request):
    """Process tier upgrade (mock — in production, use Stripe Checkout)."""
    artist = await get_current_artist(request)
    if not artist:
        raise HTTPException(status_code=401, detail="Must be logged in")

    form = await request.form()
    new_tier = form.get("tier", "free")

    if new_tier not in STORAGE_TIERS:
        raise HTTPException(status_code=400, detail="Invalid tier")

    if new_tier == "free":
        # Downgrade to free — no payment needed
        db = await get_db()
        try:
            await db.execute("UPDATE artists SET tier=? WHERE id=?", (new_tier, artist["id"]))
            await db.commit()
        finally:
            await db.close()
        return JSONResponse({"status": "ok", "message": "Downgraded to Free tier"})

    # For Pro and Label, redirect to Stripe Checkout
    tier_info = STORAGE_TIERS[new_tier]
    return JSONResponse({
        "status": "redirect",
        "message": f"Upgrade to {tier_info['name']} for ${tier_info['price_monthly']}/mo",
        "tier": new_tier,
        "price": tier_info["price_monthly"],
        "note": "In production, this would redirect to Stripe Checkout. For now, contact support to upgrade."
    })
