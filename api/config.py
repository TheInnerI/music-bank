"""
Music Bank — Configuration
"""
import os

SECRET_KEY=os.getenv("MUSIC_BANK_SECRET", "music-bank-mvp-secret-change-in-production")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 72
