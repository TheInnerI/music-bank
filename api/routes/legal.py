"""Copyright, Licensing & Protection routes."""
import json
from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import JSONResponse
from api.database import get_db
from api.templates import respond
from api.routes.auth import get_current_artist
from api.copyright import (
    LICENSE_TYPES, AI_DECLARATION_LEVELS, COPYRIGHT_RESOURCES,
    SYNC_CATEGORIES, SAMPLE_CLEARANCE_STATUS, TERMS_OF_SERVICE, DMCA_TEMPLATES,
)
from api.protection import (
    AI_TOOLS, fingerprinter, watermarker, theft_detector, legal_docs,
)

router = APIRouter()


# ============================================================
# TERMS OF SERVICE
# ============================================================

@router.get("/terms")
async def terms_of_service(request: Request):
    """Terms of Service page."""
    current_artist = await get_current_artist(request)
    return respond("legal/terms.html", {
        "request": request,
        "terms": TERMS_OF_SERVICE,
        "current_artist": current_artist,
    })


# ============================================================
# COPYRIGHT CENTER
# ============================================================

@router.get("/copyright")
async def copyright_center(request: Request):
    """Copyright registration help + resources."""
    current_artist = await get_current_artist(request)
    return respond("legal/copyright.html", {
        "request": request,
        "resources": COPYRIGHT_RESOURCES,
        "ai_tools": AI_TOOLS,
        "current_artist": current_artist,
    })


# ============================================================
# AI ARTIST RIGHTS
# ============================================================

@router.get("/ai-rights")
async def ai_rights(request: Request):
    """AI Artist Rights guide."""
    current_artist = await get_current_artist(request)
    guide = legal_docs.generate_ai_artist_rights_guide()
    return respond("legal/ai_rights.html", {
        "request": request,
        "guide": guide,
        "ai_declaration_levels": AI_DECLARATION_LEVELS,
        "ai_tools": AI_TOOLS,
        "current_artist": current_artist,
    })


# ============================================================
# LICENSE MANAGEMENT
# ============================================================

@router.get("/tracks/{track_id}/license")
async def track_license(request: Request, track_id: int):
    """View and manage a track's license."""
    current_artist = await get_current_artist(request)

    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT t.*, a.display_name as artist_name, a.username as artist_username "
            "FROM tracks t JOIN artists a ON t.artist_id=a.id WHERE t.id=?",
            (track_id,)
        )
        track = await cursor.fetchone()
        if not track:
            raise HTTPException(status_code=404, detail="Track not found")
        track = dict(track)

        # Get collaborators
        cursor = await db.execute(
            "SELECT c.*, a.display_name, a.username FROM collaborations c "
            "JOIN artists a ON c.artist_id=a.id WHERE c.track_id=?",
            (track_id,)
        )
        collaborators = [dict(c) for c in await cursor.fetchall()]

        # Get sample clearance info
        cursor = await db.execute(
            "SELECT * FROM track_samples WHERE track_id=?", (track_id,)
        )
        samples = [dict(s) for s in await cursor.fetchall()]

        # Get licensing deals
        cursor = await db.execute(
            "SELECT * FROM licensing_deals WHERE track_id=? ORDER BY created_at DESC",
            (track_id,)
        )
        deals = [dict(d) for d in await cursor.fetchall()]
    finally:
        await db.close()

    is_owner = current_artist and current_artist["id"] == track["artist_id"]

    return respond("legal/license.html", {
        "request": request,
        "track": track,
        "license_types": LICENSE_TYPES,
        "sync_categories": SYNC_CATEGORIES,
        "sample_status": SAMPLE_CLEARANCE_STATUS,
        "collaborators": collaborators,
        "samples": samples,
        "deals": deals,
        "is_owner": is_owner,
        "current_artist": current_artist,
    })


@router.post("/tracks/{track_id}/license")
async def update_track_license(request: Request, track_id: int):
    """Update a track's license settings."""
    current_artist = await get_current_artist(request)
    if not current_artist:
        raise HTTPException(status_code=401, detail="Must be logged in")

    form = await request.form()
    license_type = form.get("license_type", "all_rights_reserved")
    ai_level = form.get("ai_level", "fully_human")
    ai_tools = form.getlist("ai_tools") if hasattr(form, "getlist") else []
    sync_available = form.get("sync_available") == "on"
    sync_price = form.get("sync_price", "")

    db = await get_db()
    try:
        # Verify ownership
        cursor = await db.execute(
            "SELECT artist_id FROM tracks WHERE id=?", (track_id,)
        )
        track = await cursor.fetchone()
        if not track or track["artist_id"] != current_artist["id"]:
            raise HTTPException(status_code=403, detail="Not your track")

        # Update license
        await db.execute(
            "UPDATE tracks SET license_type=?, ai_level=?, ai_tools=?, "
            "sync_available=?, sync_price=? WHERE id=?",
            (license_type, ai_level, json.dumps(ai_tools), sync_available, sync_price, track_id)
        )
        await db.commit()
    finally:
        await db.close()

    return JSONResponse({"status": "ok", "message": "License updated"})


# ============================================================
# ROYALTY SPLITS
# ============================================================

@router.post("/tracks/{track_id}/royalty-splits")
async def update_royalty_splits(request: Request, track_id: int):
    """Update royalty splits for a collaborative track."""
    current_artist = await get_current_artist(request)
    if not current_artist:
        raise HTTPException(status_code=401, detail="Must be logged in")

    form = await request.form()

    db = await get_db()
    try:
        # Verify ownership
        cursor = await db.execute(
            "SELECT artist_id FROM tracks WHERE id=?", (track_id,)
        )
        track = await cursor.fetchone()
        if not track or track["artist_id"] != current_artist["id"]:
            raise HTTPException(status_code=403, detail="Not your track")

        # Get split data from form
        split_artists = form.getlist("split_artist_id") if hasattr(form, "getlist") else []
        split_percentages = form.getlist("split_percentage") if hasattr(form, "getlist") else []
        split_roles = form.getlist("split_role") if hasattr(form, "getlist") else []

        # Validate total = 100%
        total = sum(float(p) for p in split_percentages if p)
        if abs(total - 100.0) > 0.01:
            raise HTTPException(status_code=400, detail=f"Royalty splits must total 100%. Current: {total}%")

        # Clear existing splits
        await db.execute("DELETE FROM royalty_splits WHERE track_id=?", (track_id,))

        # Insert new splits
        for artist_id, pct, role in zip(split_artists, split_percentages, split_roles):
            if artist_id and pct:
                await db.execute(
                    "INSERT INTO royalty_splits (track_id, artist_id, percentage, role) VALUES (?,?,?,?)",
                    (track_id, int(artist_id), float(pct), role or "contributor")
                )

        # Also update collaborations table
        for artist_id, role in zip(split_artists, split_roles):
            if artist_id:
                await db.execute(
                    "INSERT OR REPLACE INTO collaborations (track_id, artist_id, role) VALUES (?,?,?)",
                    (track_id, int(artist_id), role or "contributor")
                )

        await db.commit()
    finally:
        await db.close()

    return JSONResponse({"status": "ok", "message": "Royalty splits updated"})


# ============================================================
# SAMPLE CLEARANCE
# ============================================================

@router.post("/tracks/{track_id}/samples")
async def add_sample(request: Request, track_id: int):
    """Add sample clearance info to a track."""
    current_artist = await get_current_artist(request)
    if not current_artist:
        raise HTTPException(status_code=401, detail="Must be logged in")

    form = await request.form()

    db = await get_db()
    try:
        cursor = await db.execute("SELECT artist_id FROM tracks WHERE id=?", (track_id,))
        track = await cursor.fetchone()
        if not track or track["artist_id"] != current_artist["id"]:
            raise HTTPException(status_code=403, detail="Not your track")

        await db.execute(
            "INSERT INTO track_samples (track_id, original_title, original_artist, "
            "original_label, clearance_status, clearance_notes, license_fee, royalty_percentage) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (
                track_id,
                form.get("original_title", ""),
                form.get("original_artist", ""),
                form.get("original_label", ""),
                form.get("clearance_status", "pending"),
                form.get("clearance_notes", ""),
                form.get("license_fee", ""),
                float(form.get("royalty_percentage", 0) or 0),
            )
        )
        await db.commit()
    finally:
        await db.close()

    return JSONResponse({"status": "ok", "message": "Sample info added"})


# ============================================================
# DMCA
# ============================================================

@router.get("/dmca")
async def dmca_page(request: Request):
    """DMCA information and forms."""
    current_artist = await get_current_artist(request)
    return respond("legal/dmca.html", {
        "request": request,
        "dmca_templates": DMCA_TEMPLATES,
        "current_artist": current_artist,
    })


@router.post("/dmca/report")
async def dmca_report(request: Request):
    """File a DMCA takedown report."""
    form = await request.form()

    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO dmca_reports "
            "(complainant_name, complainant_email, original_work, infringing_url, "
            "statement_good_faith, statement_accuracy, signature, status) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (
                form.get("complainant_name", ""),
                form.get("complainant_email", ""),
                form.get("original_work", ""),
                form.get("infringing_url", ""),
                form.get("statement_good_faith", ""),
                form.get("statement_accuracy", ""),
                form.get("signature", ""),
                "pending",
            )
        )
        await db.commit()
    finally:
        await db.close()

    return JSONResponse({
        "status": "ok",
        "message": "DMCA report filed. We will process within 72 hours.",
    })


# ============================================================
# OWNERSHIP CERTIFICATE
# ============================================================

@router.get("/tracks/{track_id}/certificate")
async def ownership_certificate(request: Request, track_id: int):
    """Generate ownership certificate for a track."""
    current_artist = await get_current_artist(request)

    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT t.*, a.display_name as artist_name FROM tracks t "
            "JOIN artists a ON t.artist_id=a.id WHERE t.id=?",
            (track_id,)
        )
        track = await cursor.fetchone()
        if not track:
            raise HTTPException(status_code=404, detail="Track not found")
        track = dict(track)

        # Get fingerprint
        cursor = await db.execute(
            "SELECT * FROM track_fingerprints WHERE track_id=?", (track_id,)
        )
        fp = await cursor.fetchone()
        fingerprint = dict(fp) if fp else {
            "content_hash": "not_fingerprinted",
            "perceptual_hash": "not_fingerprinted",
            "file_size": 0,
            "format": "unknown",
        }

        # Get provenance
        cursor = await db.execute(
            "SELECT * FROM track_provenance WHERE track_id=?", (track_id,)
        )
        prov = await cursor.fetchone()
        provenance = json.loads(prov["data"]) if prov else {}

        certificate = theft_detector.generate_ownership_certificate(
            artist_name=track["artist_name"],
            track_title=track["title"],
            fingerprint=fingerprint,
            provenance=provenance,
        )
    finally:
        await db.close()

    return respond("legal/certificate.html", {
        "request": request,
        "track": track,
        "certificate": certificate,
        "current_artist": current_artist,
    })


# ============================================================
# SYNC LICENSING MARKETPLACE
# ============================================================

@router.get("/licensing")
async def licensing_marketplace(request: Request):
    """Browse tracks available for sync licensing."""
    current_artist = await get_current_artist(request)

    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT t.*, a.display_name as artist_name, a.username as artist_username "
            "FROM tracks t JOIN artists a ON t.artist_id=a.id "
            "WHERE t.sync_available=1 AND t.is_published=1 "
            "ORDER BY t.plays DESC LIMIT 50"
        )
        tracks = [dict(t) for t in await cursor.fetchall()]
    finally:
        await db.close()

    return respond("legal/licensing.html", {
        "request": request,
        "tracks": tracks,
        "sync_categories": SYNC_CATEGORIES,
        "current_artist": current_artist,
    })


@router.post("/licensing/inquiry")
async def licensing_inquiry(request: Request):
    """Submit a licensing inquiry for a track."""
    current_artist = await get_current_artist(request)
    if not current_artist:
        raise HTTPException(status_code=401, detail="Must be logged in")

    form = await request.form()

    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO licensing_deals "
            "(track_id, licensee_name, licensee_email, license_type, "
            "intended_use, budget_range, status, platform_fee_cents) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (
                int(form.get("track_id", 0)),
                form.get("licensee_name", ""),
                form.get("licensee_email", ""),
                form.get("license_type", "sync"),
                form.get("intended_use", ""),
                form.get("budget_range", ""),
                "inquiry",
                0,
            )
        )
        await db.commit()
    finally:
        await db.close()

    return JSONResponse({
        "status": "ok",
        "message": "Licensing inquiry submitted. The artist will be notified.",
    })
