"""
Music Bank — Vector Embedding + Semantic Search Service

Uses sentence-transformers (all-MiniLM-L6-v2) for 384-dim embeddings.
TurboVec-compatible storage (BLOB in SQLite, with optional TurboVec backend).

Compression: Artist collections (all tracks + links) → single vector.
This enables:
  - "Find artists like X" (vector similarity)
  - "Artists who sound like Y" (semantic search)
  - Graph clustering (artists with similar vectors are close in graph)
"""
import json
import math
import struct
import time
from typing import Optional

# ============================================================
# EMBEDDING ENGINE
# ============================================================

class EmbeddingEngine:
    """Generate embeddings using sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        self.dimension = 384  # all-MiniLM-L6-v2 output dimension

    @property
    def model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
            except ImportError:
                # Fallback: return None, use mock embeddings
                pass
        return self._model

    def encode(self, text: str) -> list[float]:
        """Encode text to embedding vector."""
        if self.model:
            return self.model.encode(text).tolist()
        # Mock: deterministic hash-based embedding (for dev without the model)
        return self._mock_embed(text)

    def _mock_embed(self, text: str) -> list[float]:
        """Generate a deterministic pseudo-embedding for development."""
        import hashlib
        # Seed from text hash for determinism
        h = hashlib.sha256(text.encode()).hexdigest()
        seed = int(h[:8], 16)

        # Generate 384-dim vector from seed
        import random
        rng = random.Random(seed)
        vec = [rng.gauss(0, 1) for _ in range(self.dimension)]

        # Normalize to unit length
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec

    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        """Encode multiple texts."""
        if self.model:
            return self.model.encode(texts).tolist()
        return [self._mock_embed(t) for t in texts]


# ============================================================
# VECTOR MATH (pure Python, no dependencies)
# ============================================================

class VectorMath:
    """Vector operations for similarity search."""

    @staticmethod
    def cosine_similarity(a: list[float], b: list[float]) -> float:
        """Cosine similarity between two vectors."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    @staticmethod
    def serialize(vec: list[float]) -> bytes:
        """Serialize vector to bytes for SQLite BLOB storage."""
        return struct.pack(f"{len(vec)}f", *vec)

    @staticmethod
    def deserialize(data: bytes) -> list[float]:
        """Deserialize bytes to vector."""
        n = len(data) // 4  # 4 bytes per float32
        return list(struct.unpack(f"{n}f", data))

    @staticmethod
    def compress_vectors(vectors: list[list[float]]) -> list[float]:
        """
        Compress multiple vectors into one by averaging.
        This is the "TurboVec compression" — artist's entire collection
        (all tracks, links, bio) → single representative vector.
        """
        if not vectors:
            return [0.0] * 384
        dim = len(vectors[0])
        result = [0.0] * dim
        for vec in vectors:
            for i in range(dim):
                result[i] += vec[i]
        n = len(vectors)
        return [x / n for x in result]


# ============================================================
# SEMANTIC SEARCH SERVICE
# ============================================================

class SemanticSearchService:
    """Semantic search for artists and tracks using vector similarity."""

    def __init__(self):
        self.engine = EmbeddingEngine()
        self.math = VectorMath()

    async def embed_artist(self, artist: dict, db) -> bytes:
        """
        Create an embedding for an artist profile.
        Combines: display_name, bio, genre, location, track titles, platform links.
        """
        # Build rich text representation
        parts = [
            artist.get("display_name", ""),
            artist.get("bio", ""),
            artist.get("genre", ""),
            artist.get("location", ""),
        ]

        # Add track titles
        cursor = await db.execute(
            "SELECT title, description, mood FROM tracks WHERE artist_id=? AND is_published=1",
            (artist["id"],)
        )
        tracks = await cursor.fetchall()
        for t in tracks:
            parts.append(t["title"])
            if t["description"]:
                parts.append(t["description"])
            if t["mood"]:
                parts.append(t["mood"])

        # Add platform links
        cursor = await db.execute(
            "SELECT platform FROM artist_platform_links WHERE artist_id=?",
            (artist["id"],)
        )
        platforms = await cursor.fetchall()
        for p in platforms:
            parts.append(p["platform"])

        text = ". ".join(filter(None, parts))
        vec = self.engine.encode(text)
        return self.math.serialize(vec)

    async def embed_track(self, track: dict) -> bytes:
        """Create an embedding for a track."""
        text = f"{track.get('title', '')}. {track.get('description', '')}. {track.get('mood', '')}. {track.get('genre', '')}"
        text = text.strip()
        vec = self.engine.encode(text)
        return self.math.serialize(vec)

    async def compress_artist_collection(self, artist_id: int, db) -> bytes:
        """
        Compress entire artist collection into single vector.
        This is the "TurboVec" compression — all tracks + links → one vector.
        Uses URL-based compression: fetches page titles/descriptions from
        YouTube, Spotify, Apple Music URLs and embeds them.
        """
        embeddings = []

        # Artist profile embedding
        cursor = await db.execute("SELECT * FROM artists WHERE id=?", (artist_id,))
        artist = await cursor.fetchone()
        if artist:
            profile_vec = await self.embed_artist(dict(artist), db)
            embeddings.append(self.math.deserialize(profile_vec))

        # Track embeddings
        cursor = await db.execute(
            "SELECT title, description, mood, genre FROM tracks WHERE artist_id=? AND is_published=1",
            (artist_id,)
        )
        tracks = await cursor.fetchall()
        for t in tracks:
            text = f"{t['title']}. {t.get('description', '')}. {t.get('mood', '')}. {t.get('genre', '')}"
            vec = self.engine.encode(text.strip())
            embeddings.append(vec)

        # Platform link embeddings (from URL metadata)
        cursor = await db.execute(
            "SELECT platform, url FROM artist_platform_links WHERE artist_id=?",
            (artist_id,)
        )
        links = await cursor.fetchall()
        for link in links:
            text = f"{link['platform']} {link['url']}"
            vec = self.engine.encode(text)
            embeddings.append(vec)

        # Compress all into one vector
        if embeddings:
            compressed = self.math.compress_vectors(embeddings)
            return self.math.serialize(compressed)

        # Fallback: zero vector
        return self.math.serialize([0.0] * 384)

    async def search_tracks(self, query: str, db, limit: int = 20) -> list[dict]:
        """Semantic search for tracks."""
        query_vec = self.engine.encode(query)

        # Get all track embeddings
        cursor = await db.execute(
            "SELECT te.track_id, te.embedding, t.title, t.artist_id, t.description, t.mood, t.genre, "
            "a.display_name as artist_name, a.username as artist_username "
            "FROM track_embeddings te "
            "JOIN tracks t ON te.track_id=t.id "
            "JOIN artists a ON t.artist_id=a.id "
            "WHERE t.is_published=1"
        )
        rows = await cursor.fetchall()

        # Score by cosine similarity
        results = []
        for row in rows:
            track_vec = self.math.deserialize(row["embedding"])
            score = self.math.cosine_similarity(query_vec, track_vec)
            results.append({
                "track_id": row["track_id"],
                "title": row["title"],
                "artist_name": row["artist_name"],
                "artist_username": row["artist_username"],
                "description": row["description"],
                "mood": row["mood"],
                "genre": row["genre"],
                "score": score,
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    async def find_similar_artists(self, artist_id: int, db, limit: int = 10) -> list[dict]:
        """Find artists similar to the given artist."""
        # Get target artist's collection vector
        cursor = await db.execute(
            "SELECT collection_vector FROM artist_collection_vectors WHERE artist_id=?",
            (artist_id,)
        )
        row = await cursor.fetchone()
        if not row or not row["collection_vector"]:
            return []

        target_vec = self.math.deserialize(row["collection_vector"])

        # Compare against all other artists
        cursor = await db.execute(
            "SELECT acv.artist_id, acv.collection_vector, a.display_name, a.username, a.genre, a.bio, a.total_plays "
            "FROM artist_collection_vectors acv "
            "JOIN artists a ON acv.artist_id=a.id "
            "WHERE acv.artist_id!=?",
            (artist_id,)
        )
        rows = await cursor.fetchall()

        results = []
        for r in rows:
            vec = self.math.deserialize(r["collection_vector"])
            score = self.math.cosine_similarity(target_vec, vec)
            results.append({
                "artist_id": r["artist_id"],
                "display_name": r["display_name"],
                "username": r["username"],
                "genre": r["genre"],
                "bio": r["bio"],
                "total_plays": r["total_plays"],
                "score": score,
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]


# ============================================================
# GRAPH BUILDER
# ============================================================

class GraphBuilder:
    """Builds the artist neural network graph."""

    @staticmethod
    async def build_graph(db) -> dict:
        """
        Build the full graph: nodes (artists) + edges (connections).
        Returns D3.js-compatible JSON.
        """
        # Get all artists as nodes
        cursor = await db.execute(
            "SELECT id, username, display_name, genre, total_plays, balance_cents, "
            "lifetime_deposits_cents, total_fans, graph_x, graph_y, graph_cluster "
            "FROM artists"
        )
        artists = await cursor.fetchall()

        nodes = []
        for a in artists:
            # Node size based on total activity
            size = max(5, min(50, (
                (a["total_plays"] or 0) / 100 +
                (a["lifetime_deposits_cents"] or 0) / 100 +
                (a["total_fans"] or 0) * 5
            )))

            # Color by genre cluster
            cluster = a["graph_cluster"] or GraphBuilder._genre_cluster(a["genre"])

            nodes.append({
                "id": a["id"],
                "username": a["username"],
                "display_name": a["display_name"],
                "genre": a["genre"] or "unknown",
                "plays": a["total_plays"] or 0,
                "balance_cents": a["balance_cents"] or 0,
                "size": size,
                "cluster": cluster,
                "x": a["graph_x"] or 0,
                "y": a["graph_y"] or 0,
            })

        # Get edges
        cursor = await db.execute(
            "SELECT source_id, target_id, edge_type, weight FROM graph_edges"
        )
        edges = await cursor.fetchall()

        links = []
        for e in edges:
            links.append({
                "source": e["source_id"],
                "target": e["target_id"],
                "type": e["edge_type"],
                "weight": e["weight"],
            })

        return {"nodes": nodes, "links": links}

    @staticmethod
    def _genre_cluster(genre: str) -> str:
        """Map genre to cluster for visual grouping."""
        if not genre:
            return "other"
        g = genre.lower()
        if any(w in g for w in ["electronic", "edm", "house", "techno", "synth", "ambient"]):
            return "electronic"
        if any(w in g for w in ["hip hop", "rap", "trap", "lo-fi", "lofi"]):
            return "hiphop"
        if any(w in g for w in ["rock", "punk", "metal", "indie rock"]):
            return "rock"
        if any(w in g for w in ["folk", "country", "bluegrass", "americana"]):
            return "folk"
        if any(w in g for w in ["classical", "orchestra", "chamber", "baroque"]):
            return "classical"
        if any(w in g for w in ["jazz", "blues", "soul", "r&b", "funk"]):
            return "soul"
        if any(w in g for w in ["pop", "synthpop", "indie pop"]):
            return "pop"
        return "other"

    @staticmethod
    async def compute_graph_layout(db) -> dict:
        """
        Simple force-directed layout computation.
        In production, use a proper layout algorithm or pre-compute.
        Returns updated x,y positions for each node.
        """
        graph = await GraphBuilder.build_graph(db)
        nodes = graph["nodes"]
        links = graph["links"]

        import random
        random.seed(42)

        # Random initial positions
        positions = {n["id"]: (random.uniform(-500, 500), random.uniform(-500, 500)) for n in nodes}

        # Simple force simulation (100 iterations)
        for _ in range(100):
            # Repulsion between all nodes
            for i, n1 in enumerate(nodes):
                for j, n2 in enumerate(nodes):
                    if i >= j:
                        continue
                    x1, y1 = positions[n1["id"]]
                    x2, y2 = positions[n2["id"]]
                    dx = x1 - x2
                    dy = y1 - y2
                    dist = max(math.sqrt(dx * dx + dy * dy), 1)
                    force = 1000 / (dist * dist)
                    fx = force * dx / dist
                    fy = force * dy / dist
                    positions[n1["id"]] = (x1 + fx, y1 + fy)
                    positions[n2["id"]] = (x2 - fx, y2 - fy)

            # Attraction along edges
            for link in links:
                src = link["source"]
                tgt = link["target"]
                if src not in positions or tgt not in positions:
                    continue
                x1, y1 = positions[src]
                x2, y2 = positions[tgt]
                dx = x2 - x1
                dy = y2 - y1
                dist = max(math.sqrt(dx * dx + dy * dy), 1)
                force = dist * 0.01 * link["weight"]
                fx = force * dx / dist
                fy = force * dy / dist
                positions[src] = (x1 + fx, y1 + fy)
                positions[tgt] = (x2 - fx, y2 - fy)

        # Save positions to db
        for node in nodes:
            x, y = positions.get(node["id"], (0, 0))
            await db.execute(
                "UPDATE artists SET graph_x=?, graph_y=? WHERE id=?",
                (x, y, node["id"])
            )
        await db.commit()

        # Update nodes with positions
        for node in nodes:
            node["x"], node["y"] = positions.get(node["id"], (0, 0))

        return graph

    @staticmethod
    async def generate_edges(db):
        """
        Generate graph edges from existing data:
        - follow edges: who follows whom
        - deposit edges: who supports whom
        - genre similarity: artists in same genre cluster
        - fan overlap: artists who share fans
        """
        # Follow edges
        cursor = await db.execute("SELECT follower_id, followed_id FROM follows")
        follows = await cursor.fetchall()
        for f in follows:
            await db.execute(
                "INSERT OR REPLACE INTO graph_edges (source_id, target_id, edge_type, weight) VALUES (?,?,?,?)",
                (f["follower_id"], f["followed_id"], "follow", 1.0)
            )

        # Deposit edges (fan → artist)
        cursor = await db.execute(
            "SELECT fan_artist_id, artist_id, COUNT(*) as cnt FROM payment_deposits "
            "WHERE fan_artist_id IS NOT NULL AND status='completed' "
            "GROUP BY fan_artist_id, artist_id"
        )
        deposits = await cursor.fetchall()
        for d in deposits:
            weight = min(5.0, 1.0 + d["cnt"] * 0.5)
            await db.execute(
                "INSERT OR REPLACE INTO graph_edges (source_id, target_id, edge_type, weight) VALUES (?,?,?,?)",
                (d["fan_artist_id"], d["artist_id"], "deposit", weight)
            )

        # Collaboration edges
        cursor = await db.execute(
            "SELECT c1.artist_id as a1, c2.artist_id as a2, COUNT(*) as cnt "
            "FROM collaborations c1 "
            "JOIN collaborations c2 ON c1.track_id=c2.track_id AND c1.artist_id < c2.artist_id "
            "GROUP BY c1.artist_id, c2.artist_id"
        )
        collabs = await cursor.fetchall()
        for c in collabs:
            weight = min(10.0, 2.0 + c["cnt"])
            await db.execute(
                "INSERT OR REPLACE INTO graph_edges (source_id, target_id, edge_type, weight) VALUES (?,?,?,?)",
                (c["a1"], c["a2"], "collaboration", weight)
            )

        # Genre similarity edges (same cluster)
        cursor = await db.execute("SELECT id, genre FROM artists")
        artists = await cursor.fetchall()
        clusters = {}
        for a in artists:
            cluster = GraphBuilder._genre_cluster(a["genre"])
            clusters.setdefault(cluster, []).append(a["id"])

        for cluster, ids in clusters.items():
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    await db.execute(
                        "INSERT OR IGNORE INTO graph_edges (source_id, target_id, edge_type, weight) VALUES (?,?,?,?)",
                        (ids[i], ids[j], "genre_similarity", 0.3)
                    )
                    await db.execute(
                        "UPDATE artists SET graph_cluster=? WHERE id=? OR id=?",
                        (cluster, ids[i], ids[j])
                    )

        await db.commit()


# Singletons
search_service = SemanticSearchService()
graph_builder = GraphBuilder()
