"""Auth routes — login, register, logout"""
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Request, HTTPException
from api.database import get_db
from api.models import ArtistCreate, ArtistLogin
from api.templates import respond
from api.config import SECRET_KEY, ALGORITHM, TOKEN_EXPIRE_HOURS

router = APIRouter()


def create_token(artist_id: int) -> str:
    payload = {
        "sub": str(artist_id),
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_artist(request: Request):
    """Get current artist from JWT cookie."""
    token = request.cookies.get("mb_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        artist_id = int(payload["sub"])
        db = await get_db()
        try:
            cursor = await db.execute("SELECT * FROM artists WHERE id=?", (artist_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None
        finally:
            await db.close()
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, KeyError):
        return None


@router.get("/register")
async def register_page(request: Request):
    return respond("auth/register.html", {"request": request, "error": None})


@router.post("/register")
async def register(request: Request):
    form = await request.form()
    username = form.get("username", "").strip()
    email = form.get("email", "").strip()
    password = form.get("password", "")
    display_name = form.get("display_name", "").strip()
    genre = form.get("genre", "").strip()
    location = form.get("location", "").strip()
    bio = form.get("bio", "").strip()

    if not all([username, email, password, display_name]):
        return respond("auth/register.html", {"request": request, "error": "All required fields must be filled"})

    if len(password) < 8:
        return respond("auth/register.html", {"request": request, "error": "Password must be at least 8 characters"})

    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO artists (username, email, password_hash, display_name, bio, genre, location) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (username, email, pw_hash, display_name, bio, genre, location)
        )
        await db.commit()
        cursor = await db.execute("SELECT id FROM artists WHERE username=?", (username,))
        row = await cursor.fetchone()
        artist_id = row[0]
    except Exception as e:
        return respond("auth/register.html", {"request": request, "error": f"Registration failed: {str(e)}"})
    finally:
        await db.close()

    token = create_token(artist_id)
    response = respond("auth/register.html", {"request": request, "error": None, "success": True})
    response.set_cookie("mb_token", token, httponly=True, max_age=72 * 3600)
    return response


@router.get("/login")
async def login_page(request: Request):
    return respond("auth/login.html", {"request": request, "error": None})


@router.post("/login")
async def login(request: Request):
    form = await request.form()
    username = form.get("username", "").strip()
    password = form.get("password", "")

    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM artists WHERE username=?", (username,))
        row = await cursor.fetchone()
    finally:
        await db.close()

    if not row or not bcrypt.checkpw(password.encode(), row["password_hash"].encode()):
        return respond("auth/login.html", {"request": request, "error": "Invalid username or password"})

    token = create_token(row["id"])
    response = respond("auth/login.html", {"request": request, "error": None, "success": True})
    response.set_cookie("mb_token", token, httponly=True, max_age=72 * 3600)
    return response


@router.get("/logout")
async def logout():
    from fastapi.responses import RedirectResponse
    response = RedirectResponse(url="/")
    response.delete_cookie("mb_token")
    return response
