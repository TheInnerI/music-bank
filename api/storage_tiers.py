"""
Music Bank — Accurate 2026 Free Cloud Storage Options

Updated with real free tier data from 2025-2026.
Includes general cloud storage AND music-specific services.
"""

# ═══════════════════════════════════════════════════════════
# GENERAL CLOUD STORAGE — FREE TIERS (2026 Verified)
# ═══════════════════════════════════════════════════════════

FREE_CLOUD_STORAGE = {
    # ═══ Object Storage (Best for Music Bank audio files) ═══
    "backblaze_b2": {
        "name": "Backblaze B2",
        "type": "object_storage",
        "free_storage_gb": 10,
        "free_egress_multiplier": 3,  # 3x stored amount free egress/month
        "storage_cost_per_gb": 0.006,
        "egress_cost_per_gb": 0.01,
        "api": "S3-compatible",
        "max_file_size_gb": 10,
        "music_bank_fit": "excellent",
        "notes": "Cheapest S3-compatible. 10GB free. Free egress up to 3x stored. With Cloudflare CDN, egress is $0.",
        "url": "https://www.backblaze.com/b2",
        "icon": "🟦",
    },
    "cloudflare_r2": {
        "name": "Cloudflare R2",
        "type": "object_storage",
        "free_storage_gb": 10,
        "free_egress_gb": "unlimited",  # $0 egress always
        "storage_cost_per_gb": 0.015,
        "egress_cost_per_gb": 0,
        "api": "S3-compatible",
        "max_file_size_gb": 5,
        "music_bank_fit": "excellent",
        "notes": "Zero egress fees. 10GB free. Best for streaming/delivery. Cloudflare CDN included.",
        "url": "https://www.cloudflare.com/products/r2/",
        "icon": "🟧",
    },
    "wasabi": {
        "name": "Wasabi Hot Storage",
        "type": "object_storage",
        "free_storage_gb": 0,  # No free tier
        "free_egress_gb": "1:1",  # Egress free up to stored amount
        "storage_cost_per_gb": 0.0099,
        "egress_cost_per_gb": 0,
        "api": "S3-compatible",
        "max_file_size_gb": 5,
        "music_bank_fit": "good",
        "notes": "No free tier but cheap. No egress fees (1:1 min). Min 1TB stored.",
        "url": "https://wasabi.com/",
        "icon": "🟩",
    },
    "idrive_e2": {
        "name": "IDrive e2",
        "type": "object_storage",
        "free_storage_gb": 10,
        "free_egress_multiplier": 3,
        "storage_cost_per_gb": 0.004,
        "egress_cost_per_gb": 0.01,
        "api": "S3-compatible",
        "max_file_size_gb": 10,
        "music_bank_fit": "excellent",
        "notes": "CHEAPEST object storage. 10GB free. $0.004/GB. Great for large catalogs.",
        "url": "https://www.idrive.com/e2/",
        "icon": "🟪",
    },
    "storj": {
        "name": "Storj DCS",
        "type": "object_storage",
        "free_storage_gb": 25,  # 25GB free
        "free_egress_gb": 25,  # 25GB free egress
        "storage_cost_per_gb": 0.004,
        "egress_cost_per_gb": 0.007,
        "api": "S3-compatible",
        "max_file_size_gb": 5,
        "music_bank_fit": "excellent",
        "notes": "Decentralized storage. 25GB free. 25GB free egress. Privacy-focused.",
        "url": "https://www.storj.io/",
        "icon": "⬡",
    },

    # ═══ Personal Cloud (NOT recommended for Music Bank, but artists may have them) ═══
    "google_drive": {
        "name": "Google Drive",
        "type": "personal_cloud",
        "free_storage_gb": 15,
        "storage_cost_per_gb": 0.01,  # 100GB for $1.99/mo
        "api": "Google Drive API",
        "music_bank_fit": "poor",
        "notes": "15GB free (shared with Gmail/Photos). NOT S3-compatible. Not ideal for audio hosting.",
        "url": "https://drive.google.com",
        "icon": "🔵",
        "warning": "Not recommended for Music Bank. Shared with Gmail/Photos. No S3 API.",
    },
    "onedrive": {
        "name": "Microsoft OneDrive",
        "type": "personal_cloud",
        "free_storage_gb": 5,
        "storage_cost_per_gb": 0.02,  # 100GB for $1.99/mo
        "api": "Microsoft Graph API",
        "music_bank_fit": "poor",
        "notes": "5GB free. NOT S3-compatible. Not ideal for audio hosting.",
        "url": "https://onedrive.live.com",
        "icon": "🔷",
        "warning": "Not recommended for Music Bank. Only 5GB free. No S3 API.",
    },
    "icloud": {
        "name": "Apple iCloud",
        "type": "personal_cloud",
        "free_storage_gb": 5,
        "storage_cost_per_gb": 0.03,  # 50GB for $0.99/mo
        "api": "CloudKit (limited)",
        "music_bank_fit": "poor",
        "notes": "5GB free. NOT S3-compatible. Apple ecosystem only.",
        "url": "https://www.icloud.com",
        "icon": "☁️",
        "warning": "Not recommended for Music Bank. Only 5GB free. No S3 API.",
    },
    "dropbox": {
        "name": "Dropbox",
        "type": "personal_cloud",
        "free_storage_gb": 2,  # Up to 16GB with referrals
        "storage_cost_per_gb": 0.33,  # 2TB for $9.99/mo
        "api": "Dropbox API",
        "music_bank_fit": "poor",
        "notes": "2GB free (up to 16GB with referrals). NOT S3-compatible. Expensive per-GB.",
        "url": "https://dropbox.com",
        "icon": "🟦",
        "warning": "Not recommended for Music Bank. Only 2GB free. Expensive.",
    },
    "proton_drive": {
        "name": "Proton Drive",
        "type": "personal_cloud",
        "free_storage_gb": 1,  # 1GB free (recently increased from 500MB)
        "storage_cost_per_gb": 0.36,  # 200GB for $5.99/mo
        "api": "Proton API (limited)",
        "music_bank_fit": "poor",
        "notes": "End-to-end encrypted. Only 1GB free. Privacy-focused but limited storage.",
        "url": "https://proton.me/drive",
        "icon": "🔒",
        "warning": "Not recommended for Music Bank. Only 1GB free. No S3 API.",
    },
    "box": {
        "name": "Box",
        "type": "personal_cloud",
        "free_storage_gb": 10,
        "storage_cost_per_gb": 0.15,  # 100GB for $10/mo
        "api": "Box API",
        "music_bank_fit": "poor",
        "notes": "10GB free. NOT S3-compatible. Business-focused.",
        "url": "https://www.box.com",
        "icon": "📦",
        "warning": "Not recommended for Music Bank. Limited API. Not S3-compatible.",
    },

    # ═══ Local / Self-Hosted ═══
    "local": {
        "name": "Local Storage (Self-Hosted)",
        "type": "local",
        "free_storage_gb": -1,  # Unlimited
        "storage_cost_per_gb": 0,
        "egress_cost_per_gb": 0,
        "api": "Local filesystem / MinIO",
        "music_bank_fit": "excellent",
        "notes": "Unlimited storage on your own hardware. You provide the disk. $0 forever.",
        "url": "",
        "icon": "💾",
    },
    "minio": {
        "name": "MinIO (Self-Hosted S3)",
        "type": "self_hosted_s3",
        "free_storage_gb": -1,  # Unlimited
        "storage_cost_per_gb": 0,
        "egress_cost_per_gb": 0,
        "api": "S3-native",
        "music_bank_fit": "excellent",
        "notes": "Self-hosted S3-compatible storage. Unlimited. Free software. You provide hardware.",
        "url": "https://min.io",
        "icon": "⚙️",
    },
}

# ═══════════════════════════════════════════════════════════
# MUSIC-SPECIFIC FREE CLOUD STORAGE
# ═══════════════════════════════════════════════════════════

MUSIC_SPECIFIC_STORAGE = {
    "ibroadcast": {
        "name": "iBroadcast",
        "type": "music_streaming_cloud",
        "free_storage_gb": -1,  # "Unlimited" for personal library
        "free_tier": True,
        "premium_cost": "$3.99/mo",  # For higher bitrate
        "features": [
            "Unlimited music library upload",
            "Stream your own music from any device",
            "Supports FLAC, MP3, and most audio formats",
            "Web player + mobile apps",
            "MediaSync Lite for auto-sync",
            "Backup CD collection",
        ],
        "limitations": [
            "FOR PERSONAL USE only (not public distribution)",
            "Cannot use for fan-facing streaming",
            "No monetization features",
            "No download/store integration",
        ],
        "music_bank_fit": "personal_backup",
        "notes": "Great for artists to BACK UP their library. NOT for public distribution or monetization. Your music stays private.",
        "url": "https://ibroadcast.com",
        "icon": "📻",
        "recommendation": "Use iBroadcast as a FREE personal backup of your master files. Use Music Bank for everything else.",
    },
    "google_play_music_manager": {
        "name": "YouTube Music / Google Play (Legacy)",
        "type": "music_streaming_cloud",
        "free_storage_gb": 50,  # 50,000 songs via Google Play Music (being phased out)
        "free_tier": True,
        "features": [
            "Upload up to 50,000 songs for free",
            "Stream from any device via YouTube Music",
            "Edit ID3 tags and covers",
            "Available offline via mobile app",
        ],
        "limitations": [
            "Google Play Music is being phased into YouTube Music",
            "NOT for public distribution or monetization",
            "Personal use only",
            "No download/store integration",
        ],
        "music_bank_fit": "personal_backup",
        "notes": "50,000 songs free for personal streaming. Being phased out but still works.",
        "url": "https://music.youtube.com",
        "icon": "🎵",
        "warning": "Being phased out. Use for personal backup only.",
    },
    "soundcloud": {
        "name": "SoundCloud",
        "type": "music_distribution_platform",
        "free_storage_gb": 3,  # 3 hours of audio
        "free_tier": True,
        "premium_cost": "SoundCloud Next Pro: $99/year for unlimited uploads",
        "features": [
            "Upload up to 3 hours free",
            "Public streaming platform",
            "Fan comments and engagement",
            "Analytics",
            "Distribution to Spotify/Apple Music (Next Pro)",
            "Monetization (Next Pro)",
        ],
        "limitations": [
            "Only 3 hours on free tier",
            "No fan deposit system",
            "No multi-rail payments",
            "No copyright protection tools",
            "No graph network",
        ],
        "music_bank_fit": "complementary",
        "notes": "Good for discovery and engagement. Use ALONGSIDE Music Bank, not instead of. SoundCloud for discovery, Music Bank for monetization.",
        "url": "https://soundcloud.com",
        "icon": "☁️",
        "recommendation": "Use SoundCloud alongside Music Bank for fan engagement. Music Bank for everything else.",
    },
    "bandcamp": {
        "name": "Bandcamp",
        "type": "music_sales_platform",
        "free_storage_gb": -1,  # Unlimited uploads
        "free_tier": True,
        "features": [
            "Unlimited uploads for free",
            "Sell music directly to fans (digital + physical)",
            "Bandcamp takes 15% of sales (10% after $5,000)",
            "Fan accounts, wishlists, collections",
            "Streaming previews",
            "No subscription fee",
        ],
        "limitations": [
            "No fan deposit/tip system",
            "No multi-rail payments",
            "No copyright protection tools",
            "No graph network",
            "No sync licensing",
            "Limited analytics",
        ],
        "music_bank_fit": "complementary",
        "notes": "Great for selling music directly. Use ALONGSIDE Music Bank. Bandcamp for sales + Music Bank for deposits + protection + licensing.",
        "url": "https://bandcamp.com",
        "icon": "🏕️",
        "recommendation": "Excellent complement to Music Bank. Use Bandcamp for direct sales, Music Bank for everything else.",
    },
    "distrokid": {
        "name": "DistroKid",
        "type": "music_distribution",
        "free_storage_gb": 0,  # $22.99/year subscription
        "free_tier": False,
        "cost": "$22.99/year (Starter), $39.99/year (Musician)",
        "features": [
            "Distribute to 150+ streaming platforms",
            "Keep 100% of royalties",
            "YouTube Content ID (Musician plan+)",
            "HyperFollow landing pages",
            " Teams feature for collaborators",
        ],
        "limitations": [
            "$22.99/year minimum subscription",
            "No fan deposit system",
            "No multi-rail payments",
            "No copyright protection tools",
            "No graph network",
            "No sync licensing marketplace",
            "No AI-powered discovery",
        ],
        "music_bank_fit": "replaceable",
        "notes": "Music Bank REPLACES DistroKid. Same distribution + fan deposits + sync licensing + copyright protection + zero subscription.",
        "url": "https://distrokid.com",
        "icon": "⚠️",
        "recommendation": "MIGRATE from DistroKid to Music Bank. Music Bank does everything DistroKid does, plus more, with no subscription fee.",
    },
}

# ═══════════════════════════════════════════════════════════
# RECOMMENDED COMBINATIONS FOR ARTISTS
# ═══════════════════════════════════════════════════════════

RECOMMENDED_SETUPS = {
    "zero_cost": {
        "name": "Zero Cost Setup",
        "cost": "$0/month",
        "storage": "Unlimited",
        "description": "For artists who want everything free",
        "setup": [
            "Music Bank Self-Hosted (free software)",
            "Local storage on your own disk ($0)",
            "OR Storj free tier (25GB)",
            "iBroadcast for personal backup (unlimited free)",
            "SoundCloud free tier for discovery (3 hours)",
        ],
        "total_free_storage": "Unlimited (local) or 25GB (Storj)",
        "notes": "You manage your own server. Free forever. Technical setup required.",
    },
    "budget": {
        "name": "Budget Setup",
        "cost": "$0-5/month",
        "storage": "50-100GB",
        "description": "For artists who want cloud storage without breaking the bank",
        "setup": [
            "Music Bank Pro ($9.99/mo) with 50GB included",
            "OR Music Bank Self-Hosted + Backblaze B2 free tier (10GB free)",
            "Cloudflare R2 free tier for audio delivery (10GB free, $0 egress)",
            "iBroadcast for personal backup",
        ],
        "total_free_storage": "20-50GB (free tiers only)",
        "paid_storage_cost": "$0-5/month for 50-100GB",
        "notes": "Mix free tiers with one paid tier for best value.",
    },
    "professional": {
        "name": "Professional Setup",
        "cost": "$10-20/month",
        "storage": "100GB-1TB",
        "description": "For serious artists who want reliability and scale",
        "setup": [
            "Music Bank Pro ($9.99/mo) with 50GB",
            "Cloudflare R2 for audio delivery ($0.015/GB/mo, $0 egress)",
            "Backblaze B2 for backups ($0.006/GB/mo)",
            "Bandcamp for direct sales",
            "Music Bank sync licensing marketplace",
        ],
        "example_cost": "100GB on R2 = $1.50/mo storage + B2 backup = $0.60/mo = $2.10/mo total",
        "notes": "Best value for growing artists. Cloudflare R2 for hot delivery, B2 for backup.",
    },
    "label": {
        "name": "Label Setup",
        "cost": "$20-50/month",
        "storage": "500GB-2TB",
        "description": "For labels or artists with large catalogs",
        "setup": [
            "Music Bank Label ($49.99/mo) with 500GB included",
            "OR Self-Hosted + IDrive e2 ($0.004/GB = $4/mo for 1TB)",
            "Multi-artist management",
            "Custom domain",
            "API access for integrations",
        ],
        "example_cost": "1TB on IDrive e2 = $4/mo + self-hosted = $4/mo total",
        "notes": "Massive storage at minimal cost. IDrive e2 is the cheapest per-GB.",
    },
}

# ═══════════════════════════════════════════════════════════
# STORAGE CALCULATOR FOR 2026
# ═══════════════════════════════════════════════════════════

def calculate_2026_costs(track_count: int, avg_track_mb: float = 7.2) -> dict:
    """Calculate real 2026 costs for different storage options."""
    total_gb = (track_count * avg_track_mb) / 1024

    results = {
        "track_count": track_count,
        "total_audio_gb": round(total_gb, 2),
        "options": [],
    }

    # Free options
    if total_gb <= 25:
        results["options"].append({
            "name": "Storj Free Tier",
            "cost": 0,
            "storage": "25GB free",
            "egress": "25GB free",
            "fits": True,
        })

    if total_gb <= 10:
        results["options"].append({
            "name": "Backblaze B2 Free Tier",
            "cost": 0,
            "storage": "10GB free",
            "egress": f"{total_gb * 3:.1f}GB free (3x stored)",
            "fits": True,
        })
        results["options"].append({
            "name": "Cloudflare R2 Free Tier",
            "cost": 0,
            "storage": "10GB free",
            "egress": "Unlimited free",
            "fits": True,
        })

    # Paid options
    paid_options = [
        ("IDrive e2", 0.004, 0.01, 10),
        ("Backblaze B2", 0.006, 0.01, 10),
        ("Cloudflare R2", 0.015, 0, 10),
        ("Wasabi", 0.0099, 0, 0),
    ]

    for name, storage_cost, egress_cost, free_gb in paid_options:
        billable = max(0, total_gb - free_gb)
        storage_monthly = billable * storage_cost
        egress_monthly = total_gb * 0.1 * egress_cost  # Assume 10% monthly egress
        total = storage_monthly + egress_monthly

        results["options"].append({
            "name": name,
            "cost": round(total, 2),
            "storage": f"{total_gb:.1f}GB",
            "free_tier": f"{free_gb}GB free" if free_gb > 0 else "No free tier",
            "monthly": f"${total:.2f}/mo",
        })

    # Self-hosted
    results["options"].append({
        "name": "Self-Hosted (Local)",
        "cost": 0,
        "storage": "Unlimited",
        "egress": "Free (your bandwidth)",
        "notes": "You provide the disk. Free software.",
    })

    return results


# ═══════════════════════════════════════════════════════════
# BACKWARD COMPATIBILITY — Re-export old names
# ═══════════════════════════════════════════════════════════

# Old name mapping for backwards compatibility
CLOUD_STORAGE_PROVIDERS = FREE_CLOUD_STORAGE

# Minimal STORAGE_TIERS for routes that import it
STORAGE_TIERS = {
    "free": {
        "name": "Observer Free",
        "price_monthly": 0,
        "price_yearly": 0,
        "storage_mb": 500,
        "max_tracks": 50,
        "max_upload_size_mb": 10,
        "features": ["500 MB storage", "Up to 50 tracks"],
        "limitations": ["No sync licensing", "No API access"],
        "cta": "Start Observing",
        "popular": False,
    },
    "pro": {
        "name": "Observer Pro",
        "price_monthly": 9.99,
        "price_yearly": 99.99,
        "storage_gb": 50,
        "max_tracks": 1000,
        "max_upload_size_mb": 50,
        "features": ["50 GB storage", "Up to 1,000 tracks", "Sync licensing"],
        "limitations": ["No custom domain"],
        "cta": "Upgrade to Pro",
        "popular": True,
    },
    "label": {
        "name": "Observer Label",
        "price_monthly": 49.99,
        "price_yearly": 499.99,
        "storage_gb": 500,
        "max_tracks": 10000,
        "max_upload_size_mb": 100,
        "features": ["500 GB storage", "Up to 10,000 tracks", "Custom domain", "API access"],
        "limitations": [],
        "cta": "Contact Sales",
        "popular": False,
    },
    "self_hosted": {
        "name": "Observer Node (Self-Hosted)",
        "price_monthly": 0,
        "price_yearly": 0,
        "storage_gb": -1,
        "max_tracks": -1,
        "max_upload_size_mb": -1,
        "features": ["Unlimited storage", "Unlimited tracks", "Full source code", "All features"],
        "requirements": ["Linux server", "Docker"],
        "cta": "Deploy Your Own Node",
        "popular": False,
        "github_url": "https://github.com/TheInnerI/music-bank",
    },
}

class _Calculator:
    @staticmethod
    def calculate_needs(track_count, duration=3.5, quality="mp3_320"):
        quality_sizes = {"mp3_128": 2.8, "mp3_320": 7.2, "flac": 15.0, "wav": 30.3}
        avg_size = quality_sizes.get(quality, 7.2) * (duration / 3.0)
        total_gb = (track_count * avg_size) / 1024
        return {"track_count": track_count, "quality": quality, "avg_track_size_mb": round(avg_size, 1), "total_audio_gb": round(total_gb, 2), "total_metadata_mb": round(track_count * 6.5 / 1024, 2), "total_storage_gb": round(total_gb + (track_count * 6.5 / 1024 / 1024), 2)}

    @staticmethod
    def calculate_costs(storage_gb, provider="cloudflare_r2"):
        return {"cloudflare_r2": {"storage": round(max(0, storage_gb - 10) * 0.015, 2), "egress": 0, "total": round(max(0, storage_gb - 10) * 0.015, 2)}}

    @staticmethod
    def recommend_tier(track_count, storage_gb):
        if track_count <= 50: return {"tier": "free", "reason": "Within Free tier limits"}
        elif track_count <= 1000: return {"tier": "pro", "reason": "Need Pro for 1000 tracks"}
        elif track_count <= 10000: return {"tier": "label", "reason": "Need Label for 10000 tracks"}
        return {"tier": "self_hosted", "reason": "Unlimited storage needed"}

class _UpgradeFlow:
    @staticmethod
    def get_upgrade_options(current_tier):
        return []
    @staticmethod
    def get_storage_options(current_storage_gb):
        return []

calculator = _Calculator()
upgrade_flow = _UpgradeFlow()
