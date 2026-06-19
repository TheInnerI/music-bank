"""
Music Bank — Pydantic models
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ArtistCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str
    password: str = Field(..., min_length=8)
    display_name: str = Field(..., min_length=1, max_length=100)
    bio: str = ""
    genre: str = ""
    location: str = ""


class ArtistLogin(BaseModel):
    username: str
    password: str


class ArtistProfile(BaseModel):
    id: int
    username: str
    display_name: str
    bio: str = ""
    avatar_url: str = ""
    genre: str = ""
    location: str = ""
    created_at: str = ""
    is_verified: bool = False
    total_plays: int = 0
    total_earnings_cents: int = 0
    balance_cents: int = 0


class TrackCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    genre: str = ""
    duration_seconds: int = 0
    bpm: int = 0
    key_signature: str = ""
    mood: str = ""
    lyrics: str = ""


class TrackResponse(BaseModel):
    id: int
    artist_id: int
    artist_name: str = ""
    title: str
    description: str = ""
    genre: str = ""
    duration_seconds: int = 0
    audio_url: str = ""
    cover_url: str = ""
    bpm: int = 0
    key_signature: str = ""
    mood: str = ""
    created_at: str = ""
    plays: int = 0
    likes: int = 0
    earnings_cents: int = 0
    is_published: bool = False


class DepositCreate(BaseModel):
    track_id: int
    amount_cents: int = Field(..., ge=100)  # Minimum $1
    message: str = ""


class DiscoveryFeed(BaseModel):
    tracks: list[TrackResponse] = []
    total: int = 0
    page: int = 1
    per_page: int = 20


class BankBalance(BaseModel):
    balance_cents: int = 0
    total_earnings_cents: int = 0
    total_deposits: int = 0
    total_withdrawals: int = 0
    transactions: list[dict] = []
