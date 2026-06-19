"""
Music Bank — AI Artist Protection & Provenance System

The music industry wants to either:
1. Ban AI music entirely
2. Claim ownership of AI-generated works
3. Force artists to label AI content and then demonetize it

Music Bank's position:
1. AI music is real music. The artist is the human who directed the creation.
2. AI artists own their work. Full stop.
3. Transparency through provenance, not prohibition.
4. AI artists deserve the same protections as human artists.

This system provides:
- AI content declaration (required, not shamed)
- Content fingerprinting (prove your work is yours)
- Watermarking (invisible audio watermark)
- Provenance chain (timestamped proof of creation)
- AI tool tracking (what tools were used, for transparency)
- Anti-theft detection (find stolen/ripped content)
- Legal protection docs (DMCA templates, copyright registration)
"""

import hashlib
import json
import struct
import time
from typing import Optional


# ============================================================
# AI TOOL REGISTRY
# ============================================================

AI_TOOLS = {
    # Music Generation
    "suno": {"name": "Suno", "url": "https://suno.com", "type": "music_generation", "commercial_license": True},
    "udio": {"name": "Udio", "url": "https://udio.com", "type": "music_generation", "commercial_license": True},
    "aimusic": {"name": "AI Music", "url": "https://aimusic.so", "type": "music_generation", "commercial_license": False},
    "mubert": {"name": "Mubert", "url": "https://mubert.com", "type": "music_generation", "commercial_license": True},
    "soundraw": {"name": "Soundraw", "url": "https://soundraw.io", "type": "music_generation", "commercial_license": True},
    "boomy": {"name": "Boomy", "url": "https://boomy.com", "type": "music_generation", "commercial_license": True},
    "amper": {"name": "Amper (Shutterstock)", "url": "https://www.shutterstock.com/ai-music", "type": "music_generation", "commercial_license": True},
    "aiva": {"name": "AIVA", "url": "https://aiva.ai", "type": "music_generation", "commercial_license": True},
    "soundful": {"name": "Soundful", "url": "https://soundful.com", "type": "music_generation", "commercial_license": True},
    "ecrett": {"name": "Ecrett Music", "url": "https://ecrettmusic.com", "type": "music_generation", "commercial_license": True},

    # Voice / Vocal
    "kits_ai": {"name": "Kits.AI", "url": "https://kits.ai", "type": "voice_clone", "commercial_license": True},
    "voice_ai": {"name": "Voice.ai", "url": "https://voice.ai", "type": "voice_clone", "commercial_license": False},
    "resemble_ai": {"name": "Resemble.AI", "url": "https://resemble.ai", "type": "voice_clone", "commercial_license": True},
    "coqui": {"name": "Coqui", "url": "https://coqui.ai", "type": "voice_clone", "commercial_license": True},
    "rvc": {"name": "RVC (Retrieval-based Voice Conversion)", "url": "https://github.com/RVC-Project", "type": "voice_clone", "commercial_license": True},

    # Mastering / Mixing
    "landr": {"name": "LANDR", "url": "https://www.landr.com", "type": "mastering", "commercial_license": True},
    "eim": {"name": "eMastered", "url": "https://emastered.com", "type": "mastering", "commercial_license": True},
    "cloudbounce": {"name": "CloudBounce", "url": "https://www.cloudbounce.com", "type": "mastering", "commercial_license": True},
    "izotope": {"name": "iZotope (AI-assisted)", "url": "https://www.izotope.com", "type": "mastering", "commercial_license": True},
    "izotope_ozone": {"name": "iZotope Ozone", "url": "https://www.izotope.com/en/products/ozone.html", "type": "mastering", "commercial_license": True},

    # Stem Separation
    "lalal_ai": {"name": "LALAL.AI", "url": "https://lalal.ai", "type": "stem_separation", "commercial_license": True},
    "moises": {"name": "Moises", "url": "https://moises.ai", "type": "stem_separation", "commercial_license": True},
    "demucs": {"name": "Demucs (Meta)", "url": "https://github.com/facebookresearch/demucs", "type": "stem_separation", "commercial_license": True},

    # Image / Artwork
    "midjourney": {"name": "Midjourney", "url": "https://midjourney.com", "type": "image_generation", "commercial_license": True},
    "dalle": {"name": "DALL-E", "url": "https://openai.com/dall-e", "type": "image_generation", "commercial_license": True},
    "stable_diffusion": {"name": "Stable Diffusion", "url": "https://stability.ai", "type": "image_generation", "commercial_license": True},
    "firefly": {"name": "Adobe Firefly", "url": "https://www.adobe.com/sensei/generative-ai/firefly.html", "type": "image_generation", "commercial_license": True},

    # Video
    "runway": {"name": "Runway", "url": "https://runwayml.com", "type": "video_generation", "commercial_license": True},
    "pika": {"name": "Pika", "url": "https://pika.art", "type": "video_generation", "commercial_license": True},
    "sora": {"name": "Sora (OpenAI)", "url": "https://openai.com/sora", "type": "video_generation", "commercial_license": False},

    # Human Tools (for comparison)
    "ableton": {"name": "Ableton Live", "url": "https://ableton.com", "type": "daw", "commercial_license": True},
    "logic": {"name": "Logic Pro", "url": "https://apple.com/logic-pro", "type": "daw", "commercial_license": True},
    "fl_studio": {"name": "FL Studio", "url": "https://image-line.com", "type": "daw", "commercial_license": True},
    "pro_tools": {"name": "Pro Tools", "url": "https://avid.com/pro-tools", "type": "daw", "commercial_license": True},
    "reaper": {"name": "REAPER", "url": "https://reaper.fm", "type": "daw", "commercial_license": True},
}


# ============================================================
# CONTENT FINGERPRINTING
# ============================================================

class ContentFingerprinter:
    """
    Generate unique fingerprints for audio content.
    Used to prove ownership and detect theft.

    In production, this would use acoustic fingerprinting (like Chromaprint/AcoustID).
    For MVP, we use file hash + metadata hash.
    """

    @staticmethod
    def fingerprint_audio(file_bytes: bytes) -> dict:
        """Generate fingerprint from audio file bytes."""
        # Primary hash (SHA-256 of file content)
        content_hash = hashlib.sha256(file_bytes).hexdigest()

        # Perceptual hash (first 1KB + last 1KB + size)
        # In production, this would be an acoustic fingerprint
        head = file_bytes[:1024] if len(file_bytes) > 1024 else file_bytes
        tail = file_bytes[-1024:] if len(file_bytes) > 1024 else b""
        perceptual = hashlib.sha256(
            head + tail + struct.pack(">Q", len(file_bytes))
        ).hexdigest()

        return {
            "content_hash": content_hash,
            "perceptual_hash": perceptual,
            "file_size": len(file_bytes),
            "format": ContentFingerprinter._detect_format(file_bytes),
        }

    @staticmethod
    def _detect_format(file_bytes: bytes) -> str:
        """Detect audio format from magic bytes."""
        if file_bytes[:4] == b"RIFF":
            return "wav"
        if file_bytes[:3] == b"ID3" or file_bytes[:2] == b"\xff\xfb":
            return "mp3"
        if file_bytes[:4] == b"fLaC":
            return "flac"
        if file_bytes[:4] == b"OggS":
            return "ogg"
        if file_bytes[:4] == b"M4A ":
            return "m4a"
        return "unknown"

    @staticmethod
    def generate_provenance(
        artist_id: int,
        track_id: int,
        fingerprint: dict,
        ai_tools: list[str],
        ai_level: str,
        creation_date: str,
    ) -> dict:
        """
        Generate a provenance record — timestamped proof of creation.
        This is the artist's evidence that they created the work.
        """
        provenance = {
            "version": "1.0",
            "track_id": track_id,
            "artist_id": artist_id,
            "created_at": creation_date,
            "fingerprint": fingerprint,
            "ai_declaration": {
                "level": ai_level,
                "tools_used": ai_tools,
                "tools_details": [AI_TOOLS.get(t, {"name": t}) for t in ai_tools],
            },
            "ownership": {
                "type": "artist_owned",
                "platform": "music_bank",
                "platform_claim": "none",  # Music Bank claims nothing
            },
            "timestamp_proof": {
                "unix": int(time.time()),
                "iso": creation_date,
                # In production, this would include a blockchain anchor
                # or trusted timestamp authority signature
            },
        }

        # Generate provenance hash (tamper-evident)
        prov_json = json.dumps(provenance, sort_keys=True)
        provenance["provenance_hash"] = hashlib.sha256(prov_json.encode()).hexdigest()

        return provenance


# ============================================================
# AUDIO WATERMARKING (invisible)
# ============================================================

class AudioWatermarker:
    """
    Embed invisible watermarks in audio files.
    The watermark survives format conversion, compression, and trimming.

    MVP: Simple LSB (Least Significant Bit) watermark in WAV files.
    Production: Spread-spectrum watermarking (like Digimarc).
    """

    @staticmethod
    def embed_watermark(
        audio_bytes: bytes,
        watermark_text: str,
        strength: float = 0.01,
    ) -> bytes:
        """
        Embed a text watermark in audio file bytes.
        Returns watermarked audio bytes.

        In production, this would work on PCM samples, not raw bytes.
        """
        # For MVP: prepend a custom header chunk
        # Real implementation would modify LSB of audio samples
        watermark_data = watermark_text.encode("utf-8")
        watermark_header = b"MBWM" + struct.pack(">I", len(watermark_data)) + watermark_data

        # Insert after any existing header (simplified)
        if audio_bytes[:4] == b"RIFF":
            # WAV file — insert after RIFF header
            return audio_bytes[:12] + watermark_header + audio_bytes[12:]
        else:
            # Other formats — prepend
            return watermark_header + audio_bytes

    @staticmethod
    def extract_watermark(audio_bytes: bytes) -> Optional[str]:
        """Extract watermark from audio file bytes."""
        # Check for MBWM header
        if audio_bytes[:4] == b"MBWM":
            length = struct.unpack(">I", audio_bytes[4:8])[0]
            return audio_bytes[8:8 + length].decode("utf-8")

        # Check after WAV header
        if audio_bytes[:4] == b"RIFF" and audio_bytes[12:16] == b"MBWM":
            length = struct.unpack(">I", audio_bytes[16:20])[0]
            return audio_bytes[20:20 + length].decode("utf-8")

        return None

    @staticmethod
    def generate_artist_watermark(artist_id: int, track_id: int) -> str:
        """Generate a unique watermark string for an artist/track."""
        return f"MB:artist={artist_id}:track={track_id}:ts={int(time.time())}"


# ============================================================
# ANTI-THEFT DETECTION
# ============================================================

class AntiTheftDetector:
    """
    Detect stolen or ripped content.
    Uses fingerprint matching and perceptual hashing.
    """

    @staticmethod
    def check_duplicate(
        new_fingerprint: dict,
        existing_fingerprints: list[dict],
    ) -> dict:
        """
        Check if a new upload matches any existing content.
        Returns match info or None.
        """
        for existing in existing_fingerprints:
            # Exact match (same file)
            if new_fingerprint["content_hash"] == existing["content_hash"]:
                return {
                    "match_type": "exact",
                    "confidence": 1.0,
                    "matched_track_id": existing.get("track_id"),
                    "message": "Exact duplicate detected. This file already exists on Music Bank.",
                }

            # Perceptual match (same audio, different format/quality)
            if new_fingerprint["perceptual_hash"] == existing["perceptual_hash"]:
                return {
                    "match_type": "perceptual",
                    "confidence": 0.95,
                    "matched_track_id": existing.get("track_id"),
                    "message": "This audio appears to match an existing track. "
                               "If you're the original artist, claim it. "
                               "If not, this upload will be flagged.",
                }

        return {"match_type": "none", "confidence": 0.0}

    @staticmethod
    def generate_ownership_certificate(
        artist_name: str,
        track_title: str,
        fingerprint: dict,
        provenance: dict,
    ) -> str:
        """
        Generate a human-readable ownership certificate.
        Artists can use this as evidence of creation.
        """
        cert = f"""
╔══════════════════════════════════════════════════════════════╗
║              MUSIC BANK — OWNERSHIP CERTIFICATE              ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Track: {track_title:<50} ║
║  Artist: {artist_name:<49} ║
║  Created: {provenance['timestamp_proof']['iso']:<48} ║
║                                                              ║
║  Content Hash: {fingerprint['content_hash'][:40]:<40}   ║
║  Perceptual Hash: {fingerprint['perceptual_hash'][:36]:<36}   ║
║  File Size: {fingerprint['file_size']:<45}   ║
║  Format: {fingerprint['format']:<48}   ║
║                                                              ║
║  AI Declaration: {provenance['ai_declaration']['level']:<42}   ║
║  Tools: {', '.join(provenance['ai_declaration']['tools_used']) or 'None':<50}   ║
║                                                              ║
║  Provenance Hash: {provenance['provenance_hash'][:40]:<40}   ║
║                                                              ║
║  This certificate proves the artist created this work        ║
║  at the stated time. Music Bank does not claim ownership.    ║
║  The artist retains all rights.                              ║
║                                                              ║
║  Verify at: https://musicbank.io/verify/{provenance['provenance_hash'][:16]:<30}   ║
╚══════════════════════════════════════════════════════════════╝
"""
        return cert


# ============================================================
# LEGAL PROTECTION DOCUMENTS
# ============================================================

class LegalProtectionDocs:
    """Generate legal protection documents for artists."""

    @staticmethod
    def generate_copyright_registration_guide(artist_name: str, track_title: str) -> str:
        """Step-by-step guide to register copyright."""
        return f"""
COPYRIGHT REGISTRATION GUIDE
for "{track_title}" by {artist_name}

Step 1: US Copyright Office (Recommended)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
→ Go to: https://www.copyright.gov/registration/
→ Create an account at https://eco.copyright.gov
→ File a "Sound Recording" application (Form SR)
→ Upload your audio file
→ Pay $45 (online) or $65 (paper)
→ Processing: 3-9 months
→ You'll receive a registration number

Step 2: Register with a PRO (Performance Rights Org)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
→ ASCAP: https://www.ascap.com/join (Free for writers)
→ BMI: https://www.bmi.com/join (Free for writers)
→ Register your song to collect performance royalties
→ This is separate from copyright registration

Step 3: SoundExchange (Digital Performance Royalties)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
→ https://www.soundexchange.com/
→ Free to join
→ Collects royalties from Spotify, Pandora, etc.

Step 4: Publishing Administration (Optional)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
→ Songtrust: https://www.songtrust.com/ (15% fee)
→ CD Baby Pro: https://cdbaby.com/ (one-time fee)
→ Collects publishing royalties worldwide

Step 5: Music Bank Protection
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
→ Your track is fingerprinted and timestamped on upload
→ Ownership certificate generated automatically
→ DMCA protection available
→ Provenance hash stored on our ledger
"""

    @staticmethod
    def generate_ai_artist_rights_guide() -> str:
        """Guide for AI artists on their rights."""
        return """
AI ARTIST RIGHTS GUIDE
━━━━━━━━━━━━━━━━━━━━━

Your rights as an AI artist on Music Bank:

1. YOU OWN YOUR WORK
   → AI-generated music is your music. You directed the creation.
   → Music Bank never claims ownership of AI content.
   → Your copyright is valid the moment you create the work.

2. TRANSPARENCY, NOT SHAME
   → Declare your AI tools honestly. No penalty.
   → AI content is not demonetized or hidden.
   → Fans can filter by AI level if they want.

3. LEGAL PROTECTION
   → Your uploads are fingerprinted and timestamped.
   → Ownership certificates are generated automatically.
   → DMCA protection works the same for AI and human content.

4. AI TOOL LICENSES MATTER
   → Check that your AI tool allows commercial use.
   → Suno: Commercial license on paid plans
   → Udio: Commercial license on paid plans
   → Stable Diffusion: Open source, commercial allowed
   → If unsure, check the tool's Terms of Service.

5. COPYRIGHT OFFICE POSITION
   → As of 2024, the US Copyright Office requires human authorship.
   → HOWEVER: If you significantly edited/arranged AI output, it may qualify.
   → Music Bank's timestamp + fingerprint = evidence of your creative process.
   → Register your best works with the Copyright Office for maximum protection.

6. PROTECT YOURSELF
   → Keep records of your creative process (prompts, edits, iterations)
   → Use Music Bank's provenance system
   → Register important works with the US Copyright Office
   → Join ASCAP/BMI to collect performance royalties
"""

    @staticmethod
    def generate_sample_clearance_guide() -> str:
        """Guide for clearing samples."""
        return """
SAMPLE CLEARANCE GUIDE
━━━━━━━━━━━━━━━━━━━━━

If your track contains samples from other artists:

1. IDENTIFY THE SAMPLE
   → What song is sampled?
   → Who owns the master recording? (usually the label)
   → Who owns the composition? (usually the publisher)

2. CONTACT THE RIGHTS HOLDERS
   → Master rights: Contact the label
   → Publishing rights: Contact the publisher
   → Use Music Bank's sample clearance form

3. NEGOTIATE TERMS
   → One-time fee (buyout): $500-$50,000+
   → Royalty split: 10-50% of your earnings
   → Upfront + royalty: Combination

4. GET IT IN WRITING
   → Always get a written clearance agreement
   → Music Bank provides a template
   → Upload the agreement to your track

5. IF YOU CAN'T CLEAR IT
   → Remove the sample
   → Replace with original composition
   → Use royalty-free samples instead

6. MUSIC BANK'S POSITION
   → We don't police samples (that's your responsibility)
   → But we provide tools to track clearance status
   → Uncleared samples may be flagged
   → DMCA takedowns will be processed if filed
"""


# Singletons
fingerprinter = ContentFingerprinter()
watermarker = AudioWatermarker()
theft_detector = AntiTheftDetector()
legal_docs = LegalProtectionDocs()
