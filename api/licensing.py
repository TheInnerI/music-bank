"""
Music Bank — Autonomous Sync Licensing & Outreach System

This is the automated pipeline that:
1. Analyzes all tracks for sync licensing potential
2. Scans for licensing opportunities (film, TV, ads, games, YouTube)
3. Automatically pitches tracks to potential licensees
4. Handles negotiations and deal flow
5. Collects payments via Music Bank's multi-rail system

Pipeline:
  Upload → Analyze → Match → Pitch → Negotiate → Deal → Collect
  (AI does everything after upload)
"""
import json
import time
from typing import Optional


# ============================================================
# SYNC LICENSING ANALYZER
# ============================================================

class SyncAnalyzer:
    """Analyze tracks for sync licensing potential."""

    # Mood → Use case mapping
    MOOD_USE_CASES = {
        "epic": ["film_trailers", "video_games", "sports", "advertising"],
        "cinematic": ["film", "tv", "documentary", "corporate"],
        "upbeat": ["advertising", "youtube", "fitness", "corporate"],
        "chill": ["youtube", "podcasts", "wedding", "corporate", "documentary"],
        "dark": ["film", "tv", "video_games", "horror"],
        "emotional": ["film", "tv", "wedding", "documentary", "advertising"],
        "energetic": ["advertising", "fitness", "sports", "video_games"],
        "atmospheric": ["film", "tv", "podcasts", "documentary", "video_games"],
        "happy": ["advertising", "youtube", "wedding", "corporate"],
        "sad": ["film", "tv", "documentary", "wedding"],
        "intense": ["film", "video_games", "sports", "advertising"],
        "peaceful": ["yoga", "meditation", "spa", "documentary", "podcasts"],
        "romantic": ["wedding", "film", "tv", "advertising"],
        "suspenseful": ["film", "tv", "video_games", "podcasts"],
        "triumphant": ["sports", "film", "advertising", "corporate"],
        "raw": ["documentary", "film", "advertising"],
        "dreamy": ["film", "tv", "wedding", "youtube"],
        "aggressive": ["video_games", "sports", "film"],
        "groovy": ["advertising", "youtube", "fitness", "corporate"],
        "space": ["film", "video_games", "documentary"],
    }

    # Genre → Industry mapping
    GENRE_INDUSTRIES = {
        "electronic": ["video_games", "advertising", "youtube", "fitness", "corporate"],
        "hip hop": ["advertising", "video_games", "sports", "youtube", "film"],
        "lo-fi": ["youtube", "podcasts", "corporate", "wedding"],
        "rock": ["film", "video_games", "sports", "advertising"],
        "pop": ["advertising", "film", "tv", "wedding", "youtube"],
        "classical": ["film", "tv", "documentary", "wedding", "corporate"],
        "jazz": ["advertising", "film", "corporate", "wedding"],
        "folk": ["documentary", "film", "wedding", "advertising"],
        "trap": ["video_games", "sports", "youtube", "film"],
        "ambient": ["film", "documentary", "yoga", "meditation", "podcasts"],
        "r&b": ["advertising", "film", "tv", "wedding"],
        "country": ["advertising", "film", "wedding", "documentary"],
        "metal": ["video_games", "sports", "film"],
        "reggae": ["advertising", "film", "wedding", "corporate"],
        "latin": ["advertising", "film", "wedding", "fitness"],
        "trap metal": ["video_games", "sports", "film"],
        "jungle": ["advertising", "fitness", "video_games"],
        "space": ["film", "video_games", "documentary"],
    }

    @classmethod
    def analyze_track(cls, track: dict) -> dict:
        """
        Analyze a track for sync licensing potential.
        Returns use case recommendations and target industries.
        """
        mood = (track.get("mood", "") or "").lower()
        genre = (track.get("genre", "") or "").lower()
        duration = track.get("duration_seconds", 0)
        bpm = track.get("bpm", 0)

        # Find matching use cases
        use_cases = []
        for mood_keyword, cases in cls.MOOD_USE_CASES.items():
            if mood_keyword in mood:
                use_cases.extend(cases)

        # Find matching industries
        industries = []
        for genre_keyword, inds in cls.GENRE_INDUSTRIES.items():
            if genre_keyword in genre:
                industries.extend(inds)

        # Deduplicate
        use_cases = list(set(use_cases))
        industries = list(set(industries))

        # Calculate sync score (0-100)
        score = 0
        if use_cases: score += 30
        if industries: score += 30
        if duration > 60 and duration < 300: score += 20  # 1-5 min ideal for sync
        if bpm > 80 and bpm < 140: score += 20  # Common sync BPM range

        # Recommendations
        recommendations = []
        if "film" in use_cases:
            recommendations.append("Submit to music supervisors for film placement")
        if "video_games" in use_cases:
            recommendations.append("Pitch to game developers for soundtrack inclusion")
        if "advertising" in use_cases:
            recommendations.append("Register with music licensing libraries for ad placements")
        if "youtube" in use_cases:
            recommendations.append("Add to YouTube Audio Library for creator use")
        if "wedding" in use_cases:
            recommendations.append("Pitch to wedding videographers and planners")
        if "podcasts" in use_cases:
            recommendations.submit("Submit to podcast music libraries")
        if "fitness" in use_cases:
            recommendations.append("Pitch to fitness apps (Peloton, Nike, etc.)")
        if "corporate" in use_cases:
            recommendations.append("Register with corporate video production libraries")

        return {
            "sync_score": min(100, score),
            "use_cases": use_cases[:5],
            "target_industries": industries[:5],
            "recommendations": recommendations[:5],
            "duration_ideal": 60 <= duration <= 300,
            "bpm_ideal": 80 <= bpm <= 140,
            "ready_for_sync": score >= 50,
        }


# ============================================================
# AUTOMATED OUTREACH ENGINE
# ============================================================

class OutreachEngine:
    """
    Automatically find licensing opportunities and pitch tracks.

    In production, this would:
    1. Scrape production company databases
    2. Monitor job boards for music supervisors
    3. Use AI to find YouTube creators who need music
    4. Send personalized pitches via email
    5. Track responses and follow up
    """

    # Template pitches by use case
    PITCH_TEMPLATES = {
        "film": """Subject: {track_title} — Perfect for {use_case}

Hi {recipient_name},

I'm reaching out from Music Bank, an artist-owned music platform. I think "{track_title}" by {artist_name} would be perfect for your {use_case} project.

The track is {duration} long, {bpm} BPM, with a {mood} feel. It's available for sync licensing at {price}.

You can listen here: {track_url}
License directly: {license_url}

{music_supervisor_note}

Best,
Music Bank Licensing Team
Artist-owned. No label middleman. Direct deals.""",

        "youtube": """Subject: Royalty-free music for your YouTube channel — {track_title}

Hi {recipient_name},

Music Bank has "{track_title}" by {artist_name} available for YouTube creators.

🎵 {mood} {genre} track
⏱️ {duration} duration
💰 {price}
📄 License instantly at: {track_url}

No Content ID claims. No copyright strikes. Clear licensing upfront.

{music_supervisor_note}

Best,
Music Bank Creator Partnerships""",

        "video_games": """Subject: {track_title} — Game Soundtrack Submission

Hi {recipient_name},

Submitting "{track_title}" by {artist_name} for consideration in your game soundtrack.

Genre: {genre} | Mood: {mood} | BPM: {bpm} | Duration: {duration}
Sync-ready. Available at: {track_url}

Music Bank handles all licensing directly. No publisher involved.

Best,
Music Bank Game Audio Team""",

        "advertising": """Subject: {track_title} — Ad Campaign Music

Hi {recipient_name},

For your next ad campaign, consider "{track_title}" by {artist_name}.

{mood} {genre} energy, {bpm} BPM — ideal for {use_case}.
License price: {price}
Listen: {track_url} | License: {license_url}

Music Bank: Artist-owned music, direct licensing, no label fees.

Best,
Music Bank Licensing""",

        "wedding": """Subject: {track_title} — Wedding Videographer Music

Hi {recipient_name},

"{track_title}" by {artist_name} is perfect for wedding videos.

{mood} feel, {duration} long, romantic {genre} energy.
Royalty-free for wedding use: {track_url}

Best,
Music Bank""",

        "podcast": """Subject: {track_title} — Podcast Intro/Outro Music

Hi {recipient_name},

Your podcast needs "{track_title}" by {artist_name}.

{mood} {genre} vibe, perfect for intro/outro/transition.
Free for podcast use with attribution: {track_url}

Best,
Music Bank Podcast Partnerships""",
    }

    @classmethod
    def generate_pitch(cls, track: dict, use_case: str, recipient: dict = None) -> str:
        """Generate a pitch email for a specific use case."""
        template = cls.PITCH_TEMPLATES.get(use_use, cls.PITCH_TEMPLATES.get("film", ""))

        duration_min = track.get("duration_seconds", 0) // 60
        duration_sec = track.get("duration_seconds", 0) % 60

        return template.format(
            track_title=track.get("title", "Unknown"),
            artist_name=track.get("artist_name", "Unknown Artist"),
            use_case=use_case.replace("_", " "),
            duration=f"{duration_min}:{duration_sec:02d}",
            bpm=track.get("bpm", "N/A"),
            mood=track.get("mood", "unique"),
            genre=track.get("genre", "music"),
            price=track.get("sync_price", "Contact for pricing"),
            track_url=f"https://musicbank.io/tracks/{track.get('id', 0)}",
            license_url=f"https://musicbank.io/tracks/{track.get('id', 0)}/license",
            recipient_name=recipient.get("name", "there") if recipient else "there",
            music_supervisor_note="Direct from the artist — no label, no publisher, no middleman." if track.get("ai_level") != "fully_human" else "",
        )

    @classmethod
    def find_opportunities(cls, track: dict, use_case: str) -> list[dict]:
        """
        Find licensing opportunities for a track.

        In production, this would:
        - Query production company databases
        - Scan music supervisor directories
        - Match with YouTube creator needs
        - Connect with game developer requests

        For MVP, returns curated opportunity templates.
        """
        opportunities = []

        if use_case == "film":
            opportunities = [
                {"type": "music_supervisor", "name": "Music Supervisor Directory", "url": "https://www.musicsupervisor.com/", "description": "Submit to 500+ music supervisors"},
                {"type": "library", "name": "Musicbed", "url": "https://www.musicbed.com/", "description": "Sync licensing library — submit your best tracks"},
                {"type": "library", "name": "Artlist", "url": "https://artlist.io/", "description": "Royalty-free music for creators"},
                {"type": "library", "name": "Epidemic Sound", "url": "https://www.epidemicsound.com/", "description": "Sync licensing for content creators"},
                {"type": "marketplace", "name": "Pond5", "url": "https://www.pond5.com/", "description": "Sell music for film, TV, ads"},
            ]
        elif use_case == "youtube":
            opportunities = [
                {"type": "platform", "name": "YouTube Audio Library", "url": "https://studio.youtube.com/channel/audio", "description": "Add your music to YouTube's free audio library"},
                {"type": "library", "name": "Uppbeat", "url": "https://uppbeat.io/", "description": "Free music for YouTube creators"},
                {"type": "library", "name": "Soundstripe", "url": "https://www.soundstripe.com/", "description": "Subscription music for creators"},
            ]
        elif use_case == "video_games":
            opportunities = [
                {"type": "marketplace", "name": "GameDev Market", "url": "https://www.gamedevmarket.net/", "description": "Sell music to indie game developers"},
                {"type": "platform", "name": "Unity Asset Store", "url": "https://assetstore.unity.com/", "description": "Submit music packs for Unity games"},
                {"type": "platform", "name": "Unreal Marketplace", "url": "https://www.unrealengine.com/marketplace", "description": "Submit music for Unreal Engine games"},
                {"type": "community", "name": "IndieGameDevs", "url": "https://www.reddit.com/r/gamedev/", "description": "Connect with indie game developers"},
            ]
        elif use_case == "advertising":
            opportunities = [
                {"type": "library", "name": "Adrev", "url": "https://www.adrev.com/", "description": "License music for ads"},
                {"type": "library", "name": "Music Vine", "url": "https://www.musicvine.com/", "description": "High-quality music for advertising"},
                {"type": "marketplace", "name": "AudioJungle", "url": "https://audiojungle.net/", "description": "Sell music for commercial use"},
            ]
        elif use_case == "wedding":
            opportunities = [
                {"type": "platform", "name": "Wirestock", "url": "https://wirestock.com/", "description": "Distribute to wedding video platforms"},
                {"type": "community", "name": "Wedding Videographers Association", "url": "https://www.wvafilm.com/", "description": "Connect with wedding videographers"},
            ]
        elif use_case == "podcasts":
            opportunities = [
                {"type": "library", "name": "Podcast Music Library", "url": "https://www.podcastmusic.com/", "description": "Submit music for podcast use"},
                {"type": "library", "name": "Free Music Archive", "url": "https://freemusicarchive.org/", "description": "Free music for podcast creators"},
            ]
        elif use_case == "fitness":
            opportunities = [
                {"type": "company", "name": "Peloton", "url": "https://www.onepeloton.com/", "description": "Pitch for fitness class music"},
                {"type": "platform", "name": "Les Mills", "url": "https://www.lesmills.com/", "description": "Fitness class music licensing"},
                {"type": "app", "name": "Nike Training Club", "url": "https://www.nike.com/ntc-app", "description": "Fitness app music submissions"},
            ]

        return opportunities


# ============================================================
# LICENSING DEAL FLOW
# ============================================================

class LicensingDealFlow:
    """
    Automated deal flow for sync licensing.

    Stages:
    1. Inquiry received
    2. Track matched to use case
    3. License terms generated
    4. Contract sent
    5. Payment processed
    6. Usage rights delivered
    7. Royalty tracking activated
    """

    LICENSE_TYPES = {
        "youtube_standard": {
            "name": "YouTube Standard License",
            "price_range": "$25-$200",
            "allows": ["YouTube videos", "Monetized content", "Unlimited views"],
            "excludes": ["TV broadcast", "Film", "Advertising"],
            "duration": "Perpetual",
        },
        "podcast_standard": {
            "name": "Podcast License",
            "price_range": "$15-$100",
            "allows": ["Podcast episodes", "Monetized podcasts", "Unlimited downloads"],
            "excludes": ["TV broadcast", "Film", "Advertising"],
            "duration": "Perpetual",
        },
        "wedding": {
            "name": "Wedding/Event License",
            "price_range": "$50-$500",
            "allows": ["Wedding videos", "Event videos", "Personal use"],
            "excludes": ["Commercial use", "Broadcast", "Resale"],
            "duration": "Perpetual",
        },
        "corporate": {
            "name": "Corporate License",
            "price_range": "$200-$5000",
            "allows": ["Corporate videos", "Internal presentations", "Website"],
            "excludes": ["TV broadcast", "Public advertising", "Resale"],
            "duration": "1 year",
        },
        "film_tv": {
            "name": "Film/TV License",
            "price_range": "$500-$50,000",
            "allows": ["Film", "TV", "Streaming", "Trailers"],
            "excludes": ["Resale as standalone music"],
            "duration": "Perpetual, territory-specific",
        },
        "advertising": {
            "name": "Advertising License",
            "price_range": "$1,000-$250,000",
            "allows": ["TV ads", "Online ads", "Social media ads", "Radio ads"],
            "excludes": ["Resale as standalone music"],
            "duration": "1-3 years, territory-specific",
        },
        "video_game": {
            "name": "Video Game License",
            "price_range": "$500-$25,000",
            "allows": ["In-game music", "Game trailers", "Game marketing"],
            "excludes": ["Resale as standalone music"],
            "duration": "Perpetual, platform-specific",
        },
        "fitness": {
            "name": "Fitness License",
            "price_range": "$200-$5,000",
            "allows": ["Fitness classes", "Fitness apps", "Workout videos"],
            "excludes": ["TV broadcast", "Standalone music resale"],
            "duration": "1-2 years",
        },
    }

    @classmethod
    def generate_license_terms(cls, track: dict, license_type: str, custom_price: str = "") -> dict:
        """Generate license terms for a deal."""
        terms = cls.LICENSE_TYPES.get(license_type, cls.LICENSE_TYPES["youtube_standard"])
        return {
            "track_id": track.get("id"),
            "track_title": track.get("title"),
            "artist_name": track.get("artist_name"),
            "license_type": license_type,
            "license_name": terms["name"],
            "price": custom_price or terms["price_range"],
            "allows": terms["allows"],
            "excludes": terms["excludes"],
            "duration": terms["duration"],
            "platform_fee_cents": 0,  # Calculated on deal completion
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }


sing_analyzer = SyncAnalyzer()
outreach_engine = OutreachEngine()
deal_flow = LicensingDealFlow()
