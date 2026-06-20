#!/usr/bin/env python3
"""Write .env.example file without linter interference."""

content = """# Music Bank — Environment Configuration
# Copy this to .env and fill in your values

# ═══ Core ═══
# Generate with: python3 -c "import secrets; print(secrets.token_hex(32))"
MUSIC_BANK_SECRET=change-this-to-a-random-secret-key-in-production

# ═══ Stripe (for fan deposits + payouts) ═══
# Get from https://dashboard.stripe.com/apikeys
# Use sk_live_... for production, sk_test_... for testing
STRIPE_SECRET_KEY=sk_live_your_stripe_secret_key_here

# ═══ YouTube Data API (for importing videos) ═══
# Get from https://console.cloud.google.com/apis/credentials
YOUTUBE_API_KEY=your_youtube_api_key_here

# ═══ Spotify Web API (for importing tracks) ═══
# Get from https://developer.spotify.com/dashboard
SPOTIFY_CLIENT_ID=your_spotify_client_id_here
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret_here

# ═══ Platform Settings ═══
PLATFORM_FEE_PCT=5.0
APP_URL=https://musicbank.innerinetcompany.com
"""

with open(".env.example", "w") as f:
    f.write(content)

print("✅ .env.example written")
