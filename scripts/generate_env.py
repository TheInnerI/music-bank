#!/usr/bin/env python3
"""Generate .env file for production deployment."""

import secrets
import os

env_path = os.path.join(os.path.dirname(__file__), ".env")

secret = secrets.token_hex(32)

content = f"""# Music Bank — Environment Configuration
# Generated automatically. Edit values as needed.

# ═══ Core ═══
MUSIC_BANK_SECRET={secret}

# ═══ Stripe (for fan deposits + payouts) ═══
# Get these from https://dashboard.stripe.com/apikeys
STRIPE_SECRET_KEY=sk_live_YOUR_KEY_HERE
STRIPE_WEBHOOK_SECRET=whsec_YOUR_SECRET_HERE

# ═══ YouTube Data API (for importing videos) ═══
# Get from https://console.cloud.google.com/apis/credentials
YOUTUBE_API_KEY=YOUR_YOUTUBE_API_KEY

# ═══ Spotify Web API (for importing tracks) ═══
# Get from https://developer.spotify.com/dashboard
SPOTIFY_CLIENT_ID=YOUR_CLIENT_ID
SPOTIFY_CLIENT_SECRET=YOUR_CLIENT_SECRET

# ═══ Platform Fee (%) ═══
PLATFORM_FEE_PCT=5.0

# ═══ App URL ═══
APP_URL=https://musicbank.innerinetcompany.com
"""

with open(env_path, "w") as f:
    f.write(content)

print(f"✅ .env generated at {env_path}")
print(f"   MUSIC_BANK_SECRET={secret}")
print()
print("⚠️  Edit .env and add your Stripe/YouTube/Spotify keys:")
print(f"   nano {env_path}")
