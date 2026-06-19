"""
Music Bank — Copyright, Licensing & Artist Protection System

This is the legal backbone of Music Bank. It exists to protect artists,
not the industry. Key principles:

1. ARTISTS RETAIN ALL COPYRIGHT — Music Bank is a platform, not a label
2. AI CONTENT IS ALLOWED but must be declared — transparency, not prohibition
3. ARTISTS CHOOSE THEIR LICENSE — from All Rights Reserved to Creative Commons
4. ROYALTY SPLITS ARE AUTATIC — immutable ledger for collaborations
5. SAMPLE CLEARANCE IS TRACKED — protect artists from infringement claims
6. DMCA IS HANDLED — but with artist-first due process
7. ANTI-THEFT PROTECTION — fingerprinting, watermarking, provenance

Platform fee on licensing deals: 10% (vs 30-50% that labels take)
"""

# ============================================================
# LICENSE TYPES
# ============================================================

LICENSE_TYPES = {
    "all_rights_reserved": {
        "name": "All Rights Reserved",
        "description": "Full copyright. No one can use without explicit permission.",
        "icon": "©",
        "allows_commercial": False,
        "allows_derivatives": False,
        "requires_attribution": True,
        "share_alike": False,
    },
    "cc_by": {
        "name": "Creative Commons BY",
        "description": "Free to use with attribution.",
        "icon": "🅯",
        "allows_commercial": True,
        "allows_derivatives": True,
        "requires_attribution": True,
        "share_alike": False,
    },
    "cc_by_sa": {
        "name": "Creative Commons BY-SA",
        "description": "Free to use with attribution, derivatives must share alike.",
        "icon": "🅯🅢",
        "allows_commercial": True,
        "allows_derivatives": True,
        "requires_attribution": True,
        "share_alike": True,
    },
    "cc_by_nc": {
        "name": "Creative Commons BY-NC",
        "description": "Free for non-commercial use with attribution.",
        "icon": "🅯🅝",
        "allows_commercial": False,
        "allows_derivatives": True,
        "requires_attribution": True,
        "share_alike": False,
    },
    "cc_by_nc_sa": {
        "name": "Creative Commons BY-NC-SA",
        "description": "Non-commercial, attribution, share alike.",
        "icon": "🅯🅝🅢",
        "allows_commercial": False,
        "allows_derivatives": True,
        "requires_attribution": True,
        "share_alike": True,
    },
    "cc0": {
        "name": "CC0 (Public Domain)",
        "description": "No rights reserved. Free for any use.",
        "icon": "⓪",
        "allows_commercial": True,
        "allows_derivatives": True,
        "requires_attribution": False,
        "share_alike": False,
    },
    "sync_license": {
        "name": "Sync License Available",
        "description": "Available for film, TV, ads, games. Contact for pricing.",
        "icon": "🎬",
        "allows_commercial": True,
        "allows_derivatives": False,
        "requires_attribution": True,
        "share_alike": False,
    },
    "music_bank_exclusive": {
        "name": "Music Bank Exclusive",
        "description": "Exclusive to Music Bank. Not on Spotify, Apple Music, etc.",
        "icon": "🏦",
        "allows_commercial": False,
        "allows_derivatives": False,
        "requires_attribution": True,
        "share_alike": False,
    },
}

# ============================================================
# AI CONTENT DECLARATION LEVELS
# ============================================================

AI_DECLARATION_LEVELS = {
    "fully_human": {
        "name": "Fully Human-Created",
        "description": "No AI tools used. All performance, composition, and production is human.",
        "icon": "👤",
        "ai_percentage": 0,
    },
    "human_primary": {
        "name": "Human Primary, AI-Assisted",
        "description": "Core creative work is human. AI used for minor enhancements (mastering, noise reduction).",
        "icon": "👤🤖",
        "ai_percentage": 10,
    },
    "ai_assisted": {
        "name": "AI-Assisted",
        "description": "Significant AI involvement. Human directed the creative vision.",
        "icon": "🤖👤",
        "ai_percentage": 30,
    },
    "ai_generated_human_edited": {
        "name": "AI-Generated, Human-Edited",
        "description": "AI generated significant portions. Human edited, arranged, or performed.",
        "icon": "🤖✏️",
        "ai_percentage": 50,
    },
    "fully_ai": {
        "name": "Fully AI-Generated",
        "description": "Entirely AI-generated. Human provided prompts or direction only.",
        "icon": "🤖",
        "ai_percentage": 90,
    },
    "ai_covers": {
        "name": "AI Cover / Remix",
        "description": "AI-generated cover or remix of existing work. Original artist credited.",
        "icon": "🔄",
        "ai_percentage": 70,
    },
}

# ============================================================
# COPYRIGHT REGISTRATION HELPERS
# ============================================================

COPYRIGHT_RESOURCES = {
    "us_copyright_office": {
        "name": "US Copyright Office",
        "url": "https://www.copyright.gov/registration/",
        "description": "Official US copyright registration. $45-65 per work.",
        "processing_time": "3-9 months",
        "cost": "$45-65",
    },
    "ascap": {
        "name": "ASCAP",
        "url": "https://www.ascap.com/join",
        "description": "Performance Rights Organization. Collects royalties for public performances.",
        "processing_time": "Immediate",
        "cost": "Free for writers, $50 for publishers",
    },
    "bmi": {
        "name": "BMI",
        "url": "https://www.bmi.com/join",
        "description": "Performance Rights Organization. Free for songwriters.",
        "processing_time": "Immediate",
        "cost": "Free",
    },
    "soundexchange": {
        "name": "SoundExchange",
        "url": "https://www.soundexchange.com/",
        "description": "Collects digital performance royalties for streaming.",
        "processing_time": "2-4 weeks",
        "cost": "Free",
    },
    "pro_tip": {
        "name": "Publishing Administrator",
        "url": "https://www.songtrust.com/",
        "description": "Songtrust collects publishing royalties worldwide. 15% fee.",
        "processing_time": "2-4 weeks",
        "cost": "15% of royalties collected",
    },
}

# ============================================================
# SYNC LICENSING CATEGORIES
# ============================================================

SYNC_CATEGORIES = {
    "film": {"name": "Film / TV", "icon": "🎬", "typical_rate": "$500-$50,000"},
    "advertising": {"name": "Advertising", "icon": "📺", "typical_rate": "$1,000-$250,000"},
    "video_games": {"name": "Video Games", "icon": "🎮", "typical_rate": "$500-$25,000"},
    "podcasts": {"name": "Podcasts", "icon": "🎙️", "typical_rate": "$50-$5,000"},
    "youtube_creators": {"name": "YouTube Creators", "icon": "▶️", "typical_rate": "$25-$2,000"},
    "corporate": {"name": "Corporate / Internal", "icon": "🏢", "typical_rate": "$200-$10,000"},
    "wedding": {"name": "Wedding / Event", "icon": "💒", "typical_rate": "$100-$2,000"},
    "fitness": {"name": "Fitness / Wellness", "icon": "💪", "typical_rate": "$100-$5,000"},
    "documentary": {"name": "Documentary", "icon": "📽️", "typical_rate": "$250-$10,000"},
    "theater": {"name": "Theater / Dance", "icon": "🎭", "typical_rate": "$100-$5,000"},
}

# ============================================================
# SAMPLE CLEARANCE STATUS
# ============================================================

SAMPLE_CLEARANCE_STATUS = {
    "pending": {"name": "Pending", "color": "yellow", "description": "Clearance requested, awaiting response"},
    "approved": {"name": "Approved", "color": "green", "description": "Clearance granted, terms agreed"},
    "approved_royalty": {"name": "Approved with Royalty", "color": "blue", "description": "Clearance granted with royalty share"},
    "approved_fee": {"name": "Approved with Fee", "color": "blue", "description": "Clearance granted with one-time fee"},
    "denied": {"name": "Denied", "color": "red", "description": "Clearance denied, sample must be removed"},
    "not_required": {"name": "Not Required", "color": "gray", "description": "Original composition, no sample"},
    "expired": {"name": "Expired", "color": "red", "description": "Clearance has expired, renewal needed"},
}

# ============================================================
# TERMS OF SERVICE (key sections)
# ============================================================

TERMS_OF_SERVICE = {
    "last_updated": "2026-06-16",
    "sections": {
        "ownership": {
            "title": "Artist Ownership",
            "content": "Artists retain 100% ownership of their music, masters, and copyright. "
                       "Music Bank is a platform, not a label. We never claim ownership of your work."
        },
        "ai_content": {
            "title": "AI-Generated Content",
            "content": "AI-generated music is allowed on Music Bank. All uploads must declare "
                       "AI involvement level.Misrepresenting AI content may result in removal. "
                       "Artists are responsible for ensuring their AI tools have proper licenses."
        },
        "licensing": {
            "title": "Licensing",
            "content": "Artists choose their own license for each track. Music Bank facilitates "
                       "licensing deals and takes a 10% platform fee on sync licensing transactions. "
                       "This is significantly lower than the 30-50% that traditional publishers take."
        },
        "royalty_splits": {
            "title": "Royalty Splits",
            "content": "For collaborative works, royalty splits are recorded on an immutable ledger. "
                       "All collaborators must agree to splits before publishing. Disputes are resolved "
                       "through Music Bank mediation."
        },
        "dmca": {
            "title": "DMCA & Takedowns",
            "content": "Music Bank respects copyright. File a DMCA takedown at /dmca/report. "
                       "We process within 72 hours. Counter-notices are supported. "
                       "Repeat infringers are banned."
        },
        "sample_clearance": {
            "title": "Sample Clearance",
            "content": "Artists are responsible for clearing all samples. Music Bank provides "
                       "tools to track sample clearance status. Tracks with uncleared samples "
                       "may be flagged or removed."
        },
        "platform_fee": {
            "title": "Platform Fees",
            "content": "Music Bank takes 5% on fan deposits and 10% on sync licensing deals. "
                       "There are no subscription fees, no upload fees, and no hidden costs. "
                       "Artists earn forever from every upload."
        },
        "termination": {
            "title": "Account Termination",
            "content": "Artists can delete their account and all data at any time. "
                       "Deleted tracks are removed within 30 days. Earnings are paid out "
                       "before account closure."
        },
        "liability": {
            "title": "Limitation of Liability",
            "content": "Music Bank is a platform service. We are not responsible for "
                       "copyright infringement by users. Artists indemnify Music Bank "
                       "against claims arising from their content."
        },
    }
}

# ============================================================
# DMCA TEMPLATE
# ============================================================

DMCA_TEMPLATES = {
    "takedown_notice": """
DMCA Takedown Notice

To: Music Bank DMCA Agent
From: {complainant_name}
Date: {date}

I am the copyright owner authorized to act on behalf of the owner of the allegedly infringed work.

1. Identification of the copyrighted work: {original_work_description}
2. Identification of the infringing material: {infringing_url}
3. Statement of good faith belief: I have a good faith belief that the use is not authorized.
4. Statement of accuracy: The information is accurate and I am authorized to act.
5. Contact: {complainant_email}, {complainant_address}

Signature: {complainant_name}
""",
    "counter_notice": """
DMCA Counter-Notice

To: Music Bank DMCA Agent
From: {respondent_name}
Date: {date}

I am the user of the material that was removed or disabled.

1. Identification of the removed material: {removed_url}
2. Statement of good faith: I have a good faith belief the material was removed by mistake.
3. Consent to jurisdiction: I consent to the jurisdiction of the federal court in my district.
4. Contact: {respondent_email}, {respondent_address}

Signature: {respondent_name}
""",
}
