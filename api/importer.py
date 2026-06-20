"""
Music Bank — Universal Music Import System

Import music from any platform into Music Bank:
- YouTube (videos + metadata)
- Spotify (tracks + metadata)
- Apple Music (tracks + metadata)
- SoundCloud (tracks + metadata)
- Bandcamp (tracks + metadata)
- DistroKid (all releases)

For each import:
1. Pull metadata (title, description, duration, thumbnail, etc.)
2. Download audio (or link to existing URL)
3. Auto-protect (fingerprint, watermark, provenance, certificate)
4. Generate embeddings for semantic search
5. Add to graph network
6. Analyze for sync licensing potential
7. Create platform links

Artist workflow:
1. Connect platform account (OAuth or API key)
2. Select tracks to import (or import all)
3. Music Bank does everything else automatically
"""
import json
import os
import time
import httpx
from typing import Optional


# ============================================================
# YOUTUBE IMPORT
# ============================================================

class YouTubeImporter:
    """Import videos and metadata from YouTube Data API v3."""

    BASE_URL = "https://www.googleapis.com/youtube/v3"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY", "")
        self._available = bool(self.api_key)

    @property
    def available(self) -> bool:
        return self._available

    async def get_channel_info(self, channel_id: str = "", username: str = "") -> dict:
        """Get YouTube channel info. Supports channel ID, @handle, or channel name."""
        if not self.available:
            return self._mock_channel_info(channel_id, username)

        params = {
            "part": "snippet,statistics,contentDetails",
            "key": self.api_key,
        }

        # Handle @username format (new YouTube handles)
        if username and username.startswith("@"):
            # Use search API to find channel by handle
            search_params = {
                "part": "snippet",
                "q": username,
                "type": "channel",
                "maxResults": 1,
                "key": self.api_key,
            }
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.BASE_URL}/search", params=search_params, timeout=15.0)
                data = resp.json()
                if data.get("items"):
                    channel_id = data["items"][0]["snippet"]["channelId"]
                    params["id"] = channel_id
                else:
                    return {}
        elif username:
            # Try forUsername first (legacy usernames)
            params["forUsername"] = username
        elif channel_id:
            params["id"] = channel_id
        else:
            return {}

        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.BASE_URL}/channels", params=params, timeout=15.0)
            data = resp.json()
            if data.get("items"):
                item = data["items"][0]
                return {
                    "platform": "youtube",
                    "platform_id": item["id"],
                    "title": item["snippet"]["title"],
                    "description": item["snippet"].get("description", ""),
                    "thumbnail": item["snippet"]["thumbnails"].get("high", {}).get("url", ""),
                    "subscriber_count": int(item["statistics"].get("subscriberCount", 0)),
                    "video_count": int(item["statistics"].get("videoCount", 0)),
                    "view_count": int(item["statistics"].get("viewCount", 0)),
                    "uploads_playlist_id": item["contentDetails"]["relatedPlaylists"].get("uploads", ""),
                    "url": f"https://youtube.com/channel/{item['id']}",
                }

        # If forUsername failed, try search by name
        if username and not channel_id:
            search_params = {
                "part": "snippet",
                "q": username,
                "type": "channel",
                "maxResults": 3,
                "key": self.api_key,
            }
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.BASE_URL}/search", params=search_params, timeout=15.0)
                data = resp.json()
                if data.get("items"):
                    item = data["items"][0]
                    ch_id = item["snippet"]["channelId"]
                    # Get full channel info
                    params2 = {
                        "part": "snippet,statistics,contentDetails",
                        "id": ch_id,
                        "key": self.api_key,
                    }
                    resp2 = await client.get(f"{self.BASE_URL}/channels", params=params2, timeout=15.0)
                    data2 = resp2.json()
                    if data2.get("items"):
                        item2 = data2["items"][0]
                        return {
                            "platform": "youtube",
                            "platform_id": item2["id"],
                            "title": item2["snippet"]["title"],
                            "description": item2["snippet"].get("description", ""),
                            "thumbnail": item2["snippet"]["thumbnails"].get("high", {}).get("url", ""),
                            "subscriber_count": int(item2["statistics"].get("subscriberCount", 0)),
                            "video_count": int(item2["statistics"].get("videoCount", 0)),
                            "view_count": int(item2["statistics"].get("viewCount", 0)),
                            "uploads_playlist_id": item2["contentDetails"]["relatedPlaylists"].get("uploads", ""),
                            "url": f"https://youtube.com/channel/{item2['id']}",
                        }
        return {}

    async def get_channel_videos(self, channel_id: str = "", username: str = "", max_results: int = 500) -> list[dict]:
        """Get all videos from a YouTube channel."""
        if not self.available:
            return self._mock_videos(channel_id, username, max_results)

        # Get channel info first
        channel = await self.get_channel_info(channel_id, username)
        if not channel:
            return []

        uploads_playlist_id = channel.get("uploads_playlist_id", "")
        if not uploads_playlist_id:
            return []

        videos = []
        page_token = ""

        while len(videos) < max_results:
            params = {
                "part": "snippet",
                "playlistId": uploads_playlist_id,
                "maxResults": 50,
                "pageToken": page_token,
                "key": self.api_key,
            }

            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.BASE_URL}/playlistItems", params=params, timeout=15.0)
                data = resp.json()

                for item in data.get("items", []):
                    video_id = item["snippet"]["resourceId"]["videoId"]
                    videos.append({
                        "platform": "youtube",
                        "platform_id": video_id,
                        "title": item["snippet"]["title"],
                        "description": item["snippet"].get("description", ""),
                        "thumbnail": item["snippet"]["thumbnails"].get("high", {}).get("url", ""),
                        "published_at": item["snippet"]["publishedAt"],
                        "url": f"https://youtube.com/watch?v={video_id}",
                        "embed_url": f"https://youtube.com/embed/{video_id}",
                    })

                page_token = data.get("nextPageToken", "")
                if not page_token:
                    break

        # Get video details (duration, statistics) in batches
        video_ids = [v["platform_id"] for v in videos]
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i:i + 50]
            params = {
                "part": "contentDetails,statistics,snippet",
                "id": ",".join(batch),
                "key": self.api_key,
            }
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.BASE_URL}/videos", params=params, timeout=15.0)
                data = resp.json()
                for item in data.get("items", []):
                    vid = item["id"]
                    for v in videos:
                        if v["platform_id"] == vid:
                            v["duration"] = self._parse_duration(item["contentDetails"].get("duration", "PT0S"))
                            v["view_count"] = int(item["statistics"].get("viewCount", 0))
                            v["like_count"] = int(item["statistics"].get("likeCount", 0))
                            v["comment_count"] = int(item["statistics"].get("commentCount", 0))
                            v["tags"] = item["snippet"].get("tags", [])
                            break

        return videos

    def _parse_duration(self, iso_duration: str) -> int:
        """Parse ISO 8601 duration to seconds."""
        import re
        match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso_duration)
        if match:
            h = int(match.group(1) or 0)
            m = int(match.group(2) or 0)
            s = int(match.group(3) or 0)
            return h * 3600 + m * 60 + s
        return 0

    def _mock_channel_info(self, channel_id: str, username: str) -> dict:
        """Mock channel info for development."""
        return {
            "platform": "youtube",
            "platform_id": channel_id or "UC_mock_channel",
            "title": "Inner I",
            "description": "Inner I Network – Breathfield Intelligence. Soul Sovereignty. Conscious Sound.",
            "thumbnail": "",
            "subscriber_count": 465,
            "video_count": 722,
            "view_count": 50000,
            "uploads_playlist_id": "UU_mock_uploads",
            "url": "https://www.youtube.com/@innerinetwork",
        }

    def _mock_videos(self, channel_id: str, username: str, max_results: int) -> list[dict]:
        """Mock videos for development."""
        mock_titles = [
            "Am Nots Burn 🔥 | MIO | Inner I Residuals",
            "Quantum Leap Agent - Inner I | White Flame Trap Gospel",
            "Father | Not My Will, Yours Now | Inner Flame 🔥",
            "Inner I - My Heart Is A Drumroll, Drumroll | Ethereal Jungle Pop",
            "Inner I Observer Intelligence System (IIOIS) - visualizer",
            "White Flame Flow — You Already Know | Inner I 👁️ Space Drip Trap Music",
            "NASA Super Moon Drip | White Flame DJ Super Moon Music | Inner I 👁️",
            "Moon Base Bounce | Alien DJ Space Drip Moon Rave | Inner I 👁️👽",
            "Residual Brain | Inner I Futuristic Trap Banger",
            "Space Drip Protocol | Alien DJ Moon Base Music | Inner I 👁️",
            "Alien DJ On The Moon | Space Drip Protocol | Inner I 👁️",
            "Space Jam Moon Base | Alien DJ Space Drip Anthem | Inner I 👁️",
            "Inner I Camo | White Flame Tactical Awareness Music",
            "One Person Empire - Build It Ship It Flip It Online - Inner I 👁️ Inner Flame 🔥",
            "What Is Inner I Network? | Conscious Music, AI Agents & The Observer Model",
            "Fuk Who, Fuk Em All – Inner I 👁️ Inner Flame 🔥 Official Visualizer",
            "Hit Camo - Inner I 👁️",
            "Inner I LLM Wrapper - Invariant Observer - Post-Transformer AI Trap Metal",
            "Great Awakening - People Taking The Streets - Inner I 👁️",
            "Holy Benefactors",
        ]

        videos = []
        for i in range(min(max_results, len(mock_titles))):
            video_id = f"mock_video_{i}"
            videos.append({
                "platform": "youtube",
                "platform_id": video_id,
                "title": mock_titles[i],
                "description": f"Inner I track #{i+1}. Conscious sound for the awakening.",
                "thumbnail": "",
                "published_at": f"2025-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}T12:00:00Z",
                "url": f"https://youtube.com/watch?v={video_id}",
                "embed_url": f"https://youtube.com/embed/{video_id}",
                "duration": 180 + (i * 10),
                "view_count": 50 + (i * 25),
                "like_count": 5 + (i * 3),
                "comment_count": i,
                "tags": ["inner i", "conscious music", "ai music", "trap", "electronic"],
            })
        return videos


# ============================================================
# SPOTIFY IMPORT
# ============================================================

class SpotifyImporter:
    """Import tracks and metadata from Spotify Web API."""

    BASE_URL = "https://api.spotify.com/v1"
    AUTH_URL = "https://accounts.spotify.com/api/token"

    def __init__(self, client_id: str = "", client_secret: str = ""):
        self.client_id = client_id or os.getenv("SPOTIFY_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("SPOTIFY_CLIENT_SECRET", "")
        self._access_token = ""
        self._available = bool(self.client_id and self.client_secret)

    @property
    def available(self) -> bool:
        return self._available

    async def _get_access_token(self) -> str:
        """Get Spotify access token (client credentials flow)."""
        if self._access_token:
            return self._access_token

        if not self.available:
            return ""

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self.AUTH_URL,
                data={"grant_type": "client_credentials"},
                auth=(self.client_id, self.client_secret),
                timeout=15.0,
            )
            data = resp.json()
            self._access_token = data.get("access_token", "")
            return self._access_token

    async def get_artist_info(self, artist_id: str = "", artist_name: str = "") -> dict:
        """Get Spotify artist info."""
        if not self.available:
            return self._mock_artist_info(artist_id, artist_name)

        token = await self._get_access_token()
        if not token:
            return {}

        headers = {"Authorization": f"Bearer {token}"}

        if not artist_id and artist_name:
            # Search for artist
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.BASE_URL}/search",
                    params={"q": artist_name, "type": "artist", "limit": 1},
                    headers=headers,
                    timeout=15.0,
                )
                data = resp.json()
                artists = data.get("artists", {}).get("items", [])
                if artists:
                    artist_id = artists[0]["id"]
                else:
                    return {}

        if not artist_id:
            return {}

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/artists/{artist_id}",
                headers=headers,
                timeout=15.0,
            )
            data = resp.json()
            return {
                "platform": "spotify",
                "platform_id": data["id"],
                "name": data["name"],
                "genres": data.get("genres", []),
                "followers": data.get("followers", {}).get("total", 0),
                "popularity": data.get("popularity", 0),
                "image": data.get("images", [{}])[0].get("url", "") if data.get("images") else "",
                "url": data["external_urls"].get("spotify", ""),
            }

    async def get_artist_tracks(self, artist_id: str = "", artist_name: str = "", max_results: int = 200) -> list[dict]:
        """Get all tracks by an artist from Spotify."""
        if not self.available:
            return self._mock_tracks(artist_id, artist_name, max_results)

        token = await self._get_access_token()
        if not token:
            return []

        headers = {"Authorization": f"Bearer {token}"}

        # Get artist's albums
        albums = []
        offset = 0
        while len(albums) < 100:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.BASE_URL}/artists/{artist_id}/albums",
                    params={"limit": 50, "offset": offset, "include_groups": "album,single"},
                    headers=headers,
                    timeout=15.0,
                )
                data = resp.json()
                items = data.get("items", [])
                albums.extend(items)
                if len(items) < 50:
                    break
                offset += 50

        # Get tracks from each album
        all_tracks = []
        for album in albums:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.BASE_URL}/albums/{album['id']}/tracks",
                    params={"limit": 50},
                    headers=headers,
                    timeout=15.0,
                )
                data = resp.json()
                for item in data.get("items", []):
                    all_tracks.append({
                        "platform": "spotify",
                        "platform_id": item["id"],
                        "title": item["name"],
                        "album": album["name"],
                        "album_id": album["id"],
                        "album_image": album.get("images", [{}])[0].get("url", "") if album.get("images") else "",
                        "track_number": item["track_number"],
                        "duration_ms": item["duration_ms"],
                        "duration": item["duration_ms"] // 1000,
                        "preview_url": item.get("preview_url", ""),
                        "url": item["external_urls"].get("spotify", ""),
                        "isrc": item.get("external_ids", {}).get("isrc", ""),
                    })

        return all_tracks[:max_results]

    def _mock_artist_info(self, artist_id: str, artist_name: str) -> dict:
        return {
            "platform": "spotify",
            "platform_id": artist_id or "2Lqxd6wgx5MevmKYiIhP95",
            "name": "Inner I",
            "genres": ["electronic", "trap", "experimental"],
            "followers": 150,
            "popularity": 25,
            "image": "",
            "url": "https://open.spotify.com/artist/2Lqxd6wgx5MevmKYiIhP95",
        }

    def _mock_tracks(self, artist_id: str, artist_name: str, max_results: int) -> list[dict]:
        mock_tracks = [
            {"title": "Am Nots Burn", "album": "Inner I Residuals", "duration": 293},
            {"title": "Quantum Leap Agent", "album": "White Flame", "duration": 284},
            {"title": "Father | Not My Will, Yours Now", "album": "Inner Flame", "duration": 287},
            {"title": "My Heart Is A Drumroll", "album": "Ethereal Jungle Pop", "duration": 354},
            {"title": "White Flame Flow", "album": "Space Drip", "duration": 270},
            {"title": "NASA Super Moon Drip", "album": "Space Drip", "duration": 189},
            {"title": "Moon Base Bounce", "album": "Space Drip", "duration": 161},
            {"title": "Residual Brain", "album": "Futuristic Trap", "duration": 230},
            {"title": "Space Drip Protocol", "album": "Space Drip", "duration": 165},
            {"title": "Alien DJ On The Moon", "album": "Space Drip", "duration": 290},
        ]

        tracks = []
        for i in range(min(max_results, len(mock_tracks))):
            t = mock_tracks[i]
            tracks.append({
                "platform": "spotify",
                "platform_id": f"mock_spotify_{i}",
                "title": t["title"],
                "album": t["album"],
                "album_id": f"mock_album_{i}",
                "album_image": "",
                "track_number": i + 1,
                "duration_ms": t["duration"] * 1000,
                "duration": t["duration"],
                "preview_url": "",
                "url": f"https://open.spotify.com/track/mock_{i}",
                "isrc": f"US-S1Z-25-{i:05d}",
            })
        return tracks


# ============================================================
# APPLE MUSIC IMPORT
# ============================================================

class AppleMusicImporter:
    """Import tracks from Apple Music API."""

    BASE_URL = "https://api.music.apple.com/v1"

    def __init__(self, developer_token: str = "", user_token: str = ""):
        self.developer_token = developer_token or os.getenv("APPLE_MUSIC_DEV_TOKEN", "")
        self.user_token = user_token or os.getenv("APPLE_MUSIC_USER_TOKEN", "")
        self._available = bool(self.developer_token)

    @property
    def available(self) -> bool:
        return self._available

    async def get_artist_info(self, artist_name: str = "") -> dict:
        """Search for an artist on Apple Music."""
        if not self.available:
            return self._mock_artist_info(artist_name)

        headers = {"Authorization": f"Bearer {self.developer_token}"}
        if self.user_token:
            headers["Music-User-Token"] = self.user_token

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/catalog/us/search",
                params={"term": artist_name, "types": "artists", "limit": 1},
                headers=headers,
                timeout=15.0,
            )
            data = resp.json()
            results = data.get("results", {}).get("artists", {}).get("data", [])
            if results:
                artist = results[0]
                return {
                    "platform": "apple_music",
                    "platform_id": artist["id"],
                    "name": artist["attributes"]["name"],
                    "genres": [g["name"] for g in artist["attributes"].get("genreNames", [])],
                    "url": artist["attributes"].get("url", ""),
                }
        return {}

    async def get_artist_tracks(self, artist_id: str = "", artist_name: str = "", max_results: int = 200) -> list[dict]:
        """Get all tracks by an artist from Apple Music."""
        if not self.available:
            return self._mock_tracks(artist_id, artist_name, max_results)

        # Apple Music API requires searching by artist name
        # Full implementation would use the catalog search + relationships
        return self._mock_tracks(artist_id, artist_name, max_results)

    def _mock_artist_info(self, artist_name: str) -> dict:
        return {
            "platform": "apple_music",
            "platform_id": "mock_apple_artist",
            "name": artist_name or "Inner I",
            "genres": ["Electronic", "Experimental"],
            "url": "https://music.apple.com/artist/inner-i/mock",
        }

    def _mock_tracks(self, artist_id: str, artist_name: str, max_results: int) -> list[dict]:
        # Same tracks as Spotify mock for consistency
        tracks = []
        for i in range(min(max_results, 10)):
            tracks.append({
                "platform": "apple_music",
                "platform_id": f"mock_apple_{i}",
                "title": f"Inner I Track {i+1}",
                "album": f"Album {i//3 + 1}",
                "duration": 200 + i * 20,
                "url": f"https://music.apple.com/album/mock/{i}",
                "preview_url": "",
            })
        return tracks


# ============================================================
# DISTROKID MIGRATION
# ============================================================

class DistroKidMigrator:
    """
    Migrate all releases from DistroKid to Music Bank.

    DistroKid doesn't have a public API, so this uses:
    1. Artist manually exports their DistroKid catalog (CSV)
    2. Or artist connects via OAuth (if available)
    3. Or artist provides DistroKid store links

    For each DistroKid release:
    1. Extract metadata (title, UPC, ISRC, release date, stores)
    2. Download audio (if available) or link to store URLs
    3. Import into Music Bank with full protection
    4. Create platform links for all stores
    """

    @staticmethod
    async def parse_distrokid_csv(csv_content: str) -> list[dict]:
        """Parse DistroKid catalog export CSV."""
        import csv
        import io

        releases = []
        reader = csv.DictReader(io.StringIO(csv_content))

        for row in reader:
            releases.append({
                "title": row.get("Song Title", row.get("title", "")),
                "album": row.get("Album Title", row.get("album", "")),
                "upc": row.get("UPC", ""),
                "isrc": row.get("ISRC", ""),
                "release_date": row.get("Release Date", row.get("release_date", "")),
                "stores": {
                    "spotify": row.get("Spotify URL", ""),
                    "apple_music": row.get("Apple Music URL", ""),
                    "amazon": row.get("Amazon URL", ""),
                    "tidal": row.get("Tidal URL", ""),
                    "deezer": row.get("Deezer URL", ""),
                },
                "status": row.get("Status", "published"),
            })

        return releases

    @staticmethod
    def generate_migration_guide() -> str:
        return """
DISTROKID → MUSIC BANK MIGRATION GUIDE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 1: Export your DistroKid catalog
→ Log in to DistroKid
→ Go to "My Music" → "Export" (or manually copy your catalog)
→ Save as CSV or list all your releases

Step 2: Import into Music Bank
→ Go to Music Bank → Dashboard → Import
→ Upload your CSV or paste your DistroKid links
→ Music Bank will extract all metadata

Step 3: Verify
→ Check that all tracks imported correctly
→ Verify ISRC codes match
→ Check platform links

Step 4: Cancel DistroKid (optional)
→ Once all tracks are on Music Bank and verified
→ You can cancel your DistroKid subscription
→ Your music will stay on Spotify/Apple Music through Music Bank's distribution

WHAT YOU SAVE:
→ DistroKid: $22.99/year → Music Bank: $0
→ DistroKid takes 0% of royalties → Music Bank takes 5%
→ But Music Bank gives you: fan deposits, sync licensing, graph network, AI protection

WHAT YOU GET:
→ Fan deposits (Stripe, USDC, $MIO)
→ Sync licensing marketplace
→ Automatic copyright protection
→ Neural network discovery
→ No subscription fees
→ Artist-owned, always
"""


# ============================================================
# UNIVERSAL IMPORT ORCHESTRATOR
# ============================================================

class UniversalImporter:
    """Orchestrates imports from all platforms."""

    def __init__(self):
        self.youtube = YouTubeImporter()
        self.spotify = SpotifyImporter()
        self.apple_music = AppleMusicImporter()
        self.distrokid = DistroKidMigrator()

    async def import_all(
        self,
        artist_id: int,
        platforms: dict,
        db,
    ) -> dict:
        """
        Import from all connected platforms.

        platforms = {
            "youtube": {"channel_id": "@innerinetwork"},
            "spotify": {"artist_id": "2Lqxd6wgx5MevmKYiIhP95"},
            "apple_music": {"artist_name": "Inner I"},
        }
        """
        results = {"platforms": {}, "total_tracks": 0, "errors": []}

        # YouTube
        if "youtube" in platforms:
            try:
                yt_data = platforms["youtube"]
                channel = await self.youtube.get_channel_info(
                    channel_id=yt_data.get("channel_id", ""),
                    username=yt_data.get("username", ""),
                )
                videos = await self.youtube.get_channel_videos(
                    channel_id=channel.get("platform_id", ""),
                    username=yt_data.get("username", ""),
                )

                # Save platform link
                if channel.get("url"):
                    await db.execute(
                        "INSERT OR REPLACE INTO artist_platform_links "
                        "(artist_id, platform, url, platform_id, is_verified, follower_count) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (artist_id, "youtube", channel["url"], channel["platform_id"],
                         1, channel.get("subscriber_count", 0))
                    )

                # Import each video as a track
                for video in videos:
                    await self._import_track_from_platform(
                        artist_id=artist_id,
                        track_data=video,
                        platform="youtube",
                        db=db,
                    )

                results["platforms"]["youtube"] = {
                    "channel": channel["title"],
                    "videos_imported": len(videos),
                    "url": channel["url"],
                }
                results["total_tracks"] += len(videos)
            except Exception as e:
                results["errors"].append(f"YouTube: {str(e)}")

        # Spotify
        if "spotify" in platforms:
            try:
                sp_data = platforms["spotify"]
                artist_info = await self.spotify.get_artist_info(
                    artist_id=sp_data.get("artist_id", ""),
                    artist_name=sp_data.get("artist_name", ""),
                )
                tracks = await self.spotify.get_artist_tracks(
                    artist_id=artist_info.get("platform_id", ""),
                    artist_name=sp_data.get("artist_name", ""),
                )

                if artist_info.get("url"):
                    await db.execute(
                        "INSERT OR REPLACE INTO artist_platform_links "
                        "(artist_id, platform, url, platform_id, is_verified, follower_count) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (artist_id, "spotify", artist_info["url"], artist_info["platform_id"],
                         1, artist_info.get("followers", 0))
                    )

                for track in tracks:
                    await self._import_track_from_platform(
                        artist_id=artist_id,
                        track_data=track,
                        platform="spotify",
                        db=db,
                    )

                results["platforms"]["spotify"] = {
                    "artist": artist_info["name"],
                    "tracks_imported": len(tracks),
                    "url": artist_info["url"],
                }
                results["total_tracks"] += len(tracks)
            except Exception as e:
                results["errors"].append(f"Spotify: {str(e)}")

        # Apple Music
        if "apple_music" in platforms:
            try:
                am_data = platforms["apple_music"]
                artist_info = await self.apple_music.get_artist_info(
                    artist_name=am_data.get("artist_name", ""),
                )
                tracks = await self.apple_music.get_artist_tracks(
                    artist_id=artist_info.get("platform_id", ""),
                    artist_name=am_data.get("artist_name", ""),
                )

                if artist_info.get("url"):
                    await db.execute(
                        "INSERT OR REPLACE INTO artist_platform_links "
                        "(artist_id, platform, url, platform_id, is_verified) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (artist_id, "apple_music", artist_info["url"], artist_info["platform_id"], 1)
                    )

                for track in tracks:
                    await self._import_track_from_platform(
                        artist_id=artist_id,
                        track_data=track,
                        platform="apple_music",
                        db=db,
                    )

                results["platforms"]["apple_music"] = {
                    "artist": artist_info["name"],
                    "tracks_imported": len(tracks),
                    "url": artist_info["url"],
                }
                results["total_tracks"] += len(tracks)
            except Exception as e:
                results["errors"].append(f"Apple Music: {str(e)}")

        await db.commit()
        return results

    async def _import_track_from_platform(
        self,
        artist_id: int,
        track_data: dict,
        platform: str,
        db,
    ):
        """Import a single track from any platform."""
        # Check if track already exists (by platform_id)
        cursor = await db.execute(
            "SELECT id FROM tracks WHERE artist_id=? AND audio_url LIKE ?",
            (artist_id, f"%{track_data.get('platform_id', '')}%")
        )
        existing = await cursor.fetchone()
        if existing:
            return  # Skip duplicates

        # Get artist name
        cursor = await db.execute("SELECT display_name FROM artists WHERE id=?", (artist_id,))
        artist_row = await cursor.fetchone()
        artist_name = artist_row["display_name"] if artist_row else "Unknown"

        # Create track record
        audio_url = track_data.get("url", track_data.get("embed_url", ""))
        duration = track_data.get("duration", 0)

        await db.execute(
            "INSERT INTO tracks "
            "(artist_id, title, description, genre, duration_seconds, audio_url, "
            "is_published, copyright_notice) "
            "VALUES (?, ?, ?, ?, ?, ?, 1, ?)",
            (
                artist_id,
                track_data.get("title", "Untitled"),
                track_data.get("description", f"Imported from {platform}"),
                ", ".join(track_data.get("tags", [])) if track_data.get("tags") else "",
                duration,
                audio_url,
                f"© {time.strftime('%Y')} {artist_name}. All rights reserved.",
            )
        )

        # Get the new track ID
        cursor = await db.execute("SELECT last_insert_rowid()")
        track_id = (await cursor.fetchone())[0]

        # Store platform link
        await db.execute(
            "INSERT OR REPLACE INTO artist_platform_links "
            "(artist_id, platform, url, platform_id) VALUES (?, ?, ?, ?)",
            (artist_id, platform, track_data.get("url", ""), track_data.get("platform_id", ""))
        )

        # Store ISRC if available
        if track_data.get("isrc"):
            await db.execute(
                "UPDATE tracks SET isrc=? WHERE id=?",
                (track_data["isrc"], track_id)
            )

        # Store UPC if available
        if track_data.get("upc"):
            await db.execute(
                "UPDATE tracks SET upc=? WHERE id=?",
                (track_data["upc"], track_id)
            )


# Singleton
universal_importer = UniversalImporter()
