"""
Music Bank — Main FastAPI application
The world's first real Music Bank for independent artists.
"""
import jwt
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from api.database import init_db, seed_demo_data
from api.templates import respond
from api.routes import auth, artists, tracks, discovery, banking, api, legal, import_routes, storage_routes, upgrade_routes, agent_routes

# Configuration
from api.config import SECRET_KEY, ALGORITHM, TOKEN_EXPIRE_HOURS

BASE_DIR = Path(__file__).parent.parent

app = FastAPI(
    title="Music Bank",
    description="The world's first real Music Bank for independent artists",
    version="0.1.0",
)

# Static files
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.on_event("startup")
async def startup():
    await init_db()
    await seed_demo_data()


@app.get("/health")
async def health():
    return JSONResponse({"status": "healthy", "service": "music-bank", "version": "0.1.0"})


@app.get("/")
async def index(request: Request):
    """Landing page — discovery feed."""
    # Import here to avoid circular import
    from api.routes.discovery import discovery_feed
    return await discovery_feed(request)


# Include routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(artists.router, prefix="/artists", tags=["artists"])
app.include_router(tracks.router, prefix="/tracks", tags=["tracks"])
app.include_router(discovery.router, prefix="/discover", tags=["discovery"])
app.include_router(banking.router, prefix="/bank", tags=["banking"])
app.include_router(api.router, prefix="", tags=["api"])
app.include_router(legal.router, prefix="", tags=["legal"])
app.include_router(import_routes.router, prefix="", tags=["import"])
app.include_router(storage_routes.router, prefix="", tags=["storage"])
app.include_router(upgrade_routes.router, prefix="", tags=["upgrade"])
app.include_router(agent_routes.router, prefix="", tags=["agent"])

# Graph page
@app.get("/graph")
async def graph_page(request: Request):
    current_artist = None
    try:
        from api.routes.auth import get_current_artist
        current_artist = await get_current_artist(request)
    except:
        pass
    return respond("graph.html", {"request": request, "current_artist": current_artist})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8090)
