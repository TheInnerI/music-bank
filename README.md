# 🎵 Music Bank

**The world's first real Music Bank for independent artists.**

> Where artists deposit music and fans invest in talent. No gatekeepers. No label tax. Just music and the people who love it.

## Vision

Music Bank is designed to produce **more independent artists than the entire traditional music industry** by removing gatekeepers and giving every artist a fair shot.

### How It's Different

| Traditional Industry | Music Bank |
|---|---|
| Labels decide who gets heard | Transparent algorithm ranks by quality |
| Artists get 15-20% of revenue | Artists keep 100% (minus processing) |
| Playlist payola | Discovery score is public and auditable |
| A&R gatekeeping | Any artist can deposit music |
| Opaque contracts | Open, fair, artist-first |

## Tech Stack

- **Backend:** FastAPI (Python) + Jinja2 templates
- **Database:** SQLite (MVP) → PostgreSQL (production)
- **Frontend:** Server-rendered HTML + vanilla JS
- **Auth:** JWT cookies + bcrypt
- **Deployment:** Docker Compose + Caddy (HTTPS)
- **Payments:** Stripe Connect (production)

## Quick Start

### Local Development

```bash
cd music-bank
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn api.main:app --reload --port 8090
```

Visit: http://localhost:8090

### Docker

```bash
docker-compose up --build
```

### Demo Accounts

- Username: `luna_echo`, Password: `demo1234`
- Username: `marcus_blues`, Password: `demo1234`
- Username: `yuki_beats`, Password: `demo1234`

## Discovery Algorithm

Transparent scoring — no black box:

| Factor | Weight | Description |
|---|---|---|
| Play Velocity | 30% | Log-scaled recent plays |
| Like Ratio | 25% | Likes / Plays |
| Freshness | 20% | Newer tracks get boost (30-day decay) |
| Deposit Signals | 10% | Fan deposits = real value signal |
| Artist Engagement | 15% | Followers, upload frequency |

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/` | Landing page / discovery feed |
| GET | `/auth/register` | Register page |
| POST | `/auth/register` | Create account |
| GET | `/auth/login` | Login page |
| POST | `/auth/login` | Login |
| GET | `/auth/logout` | Logout |
| GET | `/artists/dashboard` | Artist dashboard |
| GET | `/artists/upload` | Upload page |
| POST | `/artists/upload` | Upload track |
| GET | `/artists/{username}` | Public profile |
| GET | `/tracks/{id}` | Track detail |
| POST | `/tracks/{id}/play` | Record play |
| POST | `/tracks/{id}/like` | Toggle like |
| GET | `/discover/` | Discovery feed |
| GET | `/discover/trending` | Trending tracks |
| GET | `/discover/new` | New releases |
| GET | `/discover/search?q=` | Search |
| GET | `/discover/genre/{genre}` | Browse by genre |
| GET | `/bank/` | Bank dashboard |
| POST | `/bank/deposit` | Fan deposit to artist |
| POST | `/bank/withdraw` | Withdrawal request |

## Roadmap

### MVP (v0.1) — ✅ Current
- [x] Artist registration & auth
- [x] Track upload & management
- [x] Discovery feed with transparent algorithm
- [x] Play tracking & likes
- [x] Fan deposit system (simulated)
- [x] Artist bank dashboard
- [x] Search & genre browsing

### v0.2 — Payments & Streaming
- [ ] Stripe Connect integration for real deposits
- [ ] Audio file upload to S3/CDN
- [ ] Streaming audio player with waveform
- [ ] Artist verification system

### v0.3 — Community
- [ ] Follow/following system
- [ ] Comments on tracks
- [ ] Playlists (user-created)
- [ ] Artist-to-artist collaboration tools

### v0.4 — Scale
- [ ] PostgreSQL migration
- [ ] Redis caching for discovery
- [ ] Mobile app (React Native)
- [ ] API for third-party integrations

## Built By

[Inner I Network](https://innerinetcompany.com) — Building systems that serve truth, love, and human flourishing.

---

#inneri #inneri76 #music-bank #mvp
