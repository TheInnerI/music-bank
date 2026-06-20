#!/usr/bin/env python3
"""Write correct .env.example with 3 Stripe keys."""

content = """# Music Bank — Environment Configuration

# ═══ Core ═══
# Generate: python3 -c "import secrets; print(secrets.token_hex(32))"
MUSIC_BANK_SECRET=your-r...n
# ═══ Stripe (3 keys needed) ═══
# Get from https://dashboard.stripe.com/apikeys
STRIPE_SECRET_KEY=*** STRIPE_PUBLISHABLE_KEY=*** STRIPE_WEBHOOK_SECRET=*** ═══ YouTube Data API (for importing videos) ═══
# Get from https://console.cloud.google.com/apis/credentials
YOUTUBE_API_KEY=YOUR_Y...n
# ═══ Spotify Web API (for importing tracks) ═══
# Get from https://developer.spotify.com/dashboard
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_s...n
# ═══ Base/USDC (for crypto payments) ═══
# Your Base wallet address that receives USDC deposits
BASE_PLATFORM_WALLET=0x...

# ═══ $MIO Token (for MIO payments on Base) ═══
# MIO token contract address on Base mainnet
MIO_CONTRACT_ADDRESS=0x...

# ═══ Platform Settings ═══
PLATFORM_FEE_PCT=5.0
APP_URL=https://musicbank.innerinetcompany.com
"""

with open(".env.example", "w") as f:
    f.write(content)

print("OK - .env.example written with 3 Stripe keys")
