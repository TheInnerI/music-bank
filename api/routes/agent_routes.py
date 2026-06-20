"""MIO Agent routes — ACP job offerings and callbacks."""
from fastapi import APIRouter, Request, HTTPException
from api.database import get_db
from api.templates import respond
from api.routes.auth import get_current_artist
from api.mio_agent import mio_job_service
from api.config import MIO_AGENT_WALLET, MIO_AGENT_ID, MIO_AGENT_URL

router = APIRouter()


@router.get("/agents/mio")
async def mio_agent_page(request: Request):
    """MIO Evaluator agent page — services and pricing."""
    current_artist = await get_current_artist(request)
    tiers = mio_job_service.get_service_tiers()

    artist_tracks = []
    if current_artist:
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT id, title, plays FROM tracks WHERE artist_id=? ORDER BY created_at DESC LIMIT 50",
                (current_artist["id"],)
            )
            artist_tracks = [dict(r) for r in await cursor.fetchall()]
        finally:
            await db.close()

    return respond("agents/mio.html", {
        "request": request,
        "current_artist": current_artist,
        "tiers": tiers,
        "artist_tracks": artist_tracks,
        "agent_wallet": MIO_AGENT_WALLET,
        "agent_id": MIO_AGENT_ID,
        "agent_url": MIO_AGENT_URL,
    })


@router.post("/api/agent/evaluate")
async def create_evaluation(request: Request):
    """Create an evaluation job with the MIO agent."""
    current_artist = await get_current_artist(request)
    if not current_artist:
        raise HTTPException(status_code=401, detail="Must be logged in")

    form = await request.form()
    track_id = int(form.get("track_id", 0))
    eval_type = form.get("eval_type", "standard_eval")

    # Verify track belongs to artist
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id, title FROM tracks WHERE id=? AND artist_id=?",
            (track_id, current_artist["id"])
        )
        track = await cursor.fetchone()
    finally:
        await db.close()

    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    # Create evaluation job (Virtuals returns results immediately)
    result = await mio_job_service.create_job(
        track_id=track_id,
        track_title=track["title"],
        artist_name=current_artist["display_name"],
        eval_type=eval_type,
    )

    from fastapi.responses import JSONResponse
    return JSONResponse({
        "status": result.get("status", "ok"),
        "job_id": result.get("job_id"),
        "message": result.get("message", "Evaluation complete!"),
        "result": result.get("result"),  # Include results directly
    })


@router.get("/api/agent/status/{job_id}")
async def check_evaluation_status(request: Request, job_id: str):
    """Check status of an evaluation job."""
    current_artist = await get_current_artist(request)
    if not current_artist:
        raise HTTPException(status_code=401, detail="Must be logged in")

    result = await mio_job_service.get_job_status(job_id)
    from fastapi.responses import JSONResponse
    return JSONResponse(result)


@router.get("/api/agent/evaluations")
async def list_evaluations(request: Request):
    """List all evaluations for the current artist."""
    current_artist = await get_current_artist(request)
    if not current_artist:
        raise HTTPException(status_code=401, detail="Must be logged in")

    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT ae.id, ae.job_id, ae.track_id, ae.eval_type, ae.score, ae.feedback, ae.status, ae.created_at, t.title as track_title "
            "FROM agent_evaluations ae "
            "LEFT JOIN tracks t ON ae.track_id=t.id "
            "WHERE t.artist_id=? OR ae.track_id IN (SELECT id FROM tracks WHERE artist_id=?) "
            "ORDER BY ae.created_at DESC LIMIT 50",
            (current_artist["id"], current_artist["id"])
        )
        evals = [dict(r) for r in await cursor.fetchall()]
    finally:
        await db.close()

    return JSONResponse({"evaluations": evals})


@router.post("/api/agent/callback")
async def agent_callback(request: Request):
    """Callback endpoint for MIO agent to send results."""
    data = await request.json()
    job_id = data.get("job_id")
    result = data.get("result", {})
    status = data.get("status", "completed")

    # Store result in database
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO agent_evaluations (job_id, track_id, eval_type, score, feedback, status, raw_result) VALUES (?,?,?,?,?,?,?)",
            (
                job_id,
                data.get("track_id"),
                data.get("eval_type"),
                result.get("score"),
                result.get("feedback", ""),
                status,
                json.dumps(result),
            )
        )
        await db.commit()
    finally:
        await db.close()

    return {"status": "ok"}
