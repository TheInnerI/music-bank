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


# ═══ Password Reset ═══

@router.get("/forgot-password")
async def forgot_password_page(request: Request):
    return respond("auth/forgot_password.html", {"request": request, "error": None, "success": None})


@router.post("/forgot-password")
async def forgot_password(request: Request):
    form = await request.form()
    email = form.get("email", "").strip().lower()

    if not email:
        return respond("auth/forgot_password.html", {"request": request, "error": "Email is required", "success": None})

    db = await get_db()
    try:
        cursor = await db.execute("SELECT id, display_name, email FROM artists WHERE email=?", (email,))
        artist = await cursor.fetchone()
    finally:
        await db.close()

    if not artist:
        # Don't reveal if email exists
        return respond("auth/forgot_password.html", {"request": request, "error": None, "success": "If an account exists with that email, a reset link has been sent."})

    # Generate reset token (valid 1 hour)
    import secrets
    reset_token = secrets.token_urlsafe(32)
    token_hash = bcrypt.hashpw(reset_token.encode(), bcrypt.gensalt()).decode()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO password_resets (artist_id, token_hash, expires_at) VALUES (?,?,?)",
            (artist["id"], token_hash, expires_at.isoformat())
        )
        await db.commit()
    finally:
        await db.close()

    # Send reset email
    from api.email_service import email_service
    await email_service.send_password_reset(
        to_email=artist["email"],
        reset_token=reset_token,
        artist_name=artist["display_name"]
    )

    return respond("auth/forgot_password.html", {"request": request, "error": None, "success": "If an account exists with that email, a reset link has been sent."})


@router.get("/reset-password")
async def reset_password_page(request: Request):
    token = request.query_params.get("token", "")
    if not token:
        raise HTTPException(status_code=400, detail="Invalid token")
    return respond("auth/reset_password.html", {"request": request, "token": token, "error": None})


@router.post("/reset-password")
async def reset_password(request: Request):
    form = await request.form()
    token = form.get("token", "")
    new_password = form.get("password", "")

    if not token or not new_password:
        return respond("auth/reset_password.html", {"request": request, "token": token, "error": "Password is required"})

    if len(new_password) < 8:
        return respond("auth/reset_password.html", {"request": request, "token": token, "error": "Password must be at least 8 characters"})

    db = await get_db()
    try:
        # Find valid reset token
        cursor = await db.execute(
            "SELECT pr.artist_id, pr.token_hash, pr.expires_at FROM password_resets pr WHERE pr.used=0"
        )
        rows = await cursor.fetchall()

        artist_id = None
        for row in rows:
            if bcrypt.checkpw(token.encode(), row["token_hash"].encode()):
                expires = datetime.fromisoformat(row["expires_at"])
                if datetime.now(timezone.utc) < expires:
                    artist_id = row["artist_id"]
                    break

        if not artist_id:
            return respond("auth/reset_password.html", {"request": request, "token": "", "error": "Invalid or expired token"})

        # Update password
        pw_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        await db.execute("UPDATE artists SET password_hash=? WHERE id=?", (pw_hash, artist_id))
        await db.execute("UPDATE password_resets SET used=1 WHERE artist_id=?", (artist_id,))
        await db.commit()
    finally:
        await db.close()

    return respond("auth/login.html", {"request": request, "error": None, "success": "Password reset successfully! You can now log in."})
