"""
Music Bank — Lightweight Semantic Search Engine

Uses TF-IDF + SVD for semantic embeddings without heavy dependencies.
No sentence-transformers needed — works with standard library + numpy.

For better results, install sentence-transformers:
    pip install sentence-transformers
"""

import json
import math
import re
import sqlite3
from typing import Optional
from pathlib import Path


class LightweightEmbeddingEngine:
    """Generate embeddings using TF-IDF + SVD (no heavy dependencies)."""

    def __init__(self, dimension: int = 128):
        self.dimension = dimension
        self._vocabulary = {}
        self._idf = {}
        self._svd_components = None
        self._fitted = False

    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenizer."""
        text = text.lower()
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        tokens = text.split()
        # Remove very short tokens
        return [t for t in tokens if len(t) > 1]

    def _compute_tfidf(self, documents: list[str]) -> list[list[float]]:
        """Compute TF-IDF vectors for documents."""
        # Build vocabulary
        df = {}  # document frequency
        tf_list = []  # term frequency for each doc

        for doc in documents:
            tokens = self._tokenize(doc)
            tf = {}
            for token in tokens:
                tf[token] = tf.get(token, 0) + 1
            tf_list.append(tf)

            # Document frequency
            seen = set(tokens)
            for token in seen:
                df[token] = df.get(token, 0) + 1

        # Build vocabulary (top N terms by frequency)
        sorted_terms = sorted(df.items(), key=lambda x: x[1], reverse=True)
        vocab_size = min(len(sorted_terms), 5000)
        self._vocabulary = {term: i for i, (term, _) in enumerate(sorted_terms[:vocab_size])}

        # Compute IDF
        n_docs = len(documents)
        self._idf = {term: math.log(n_docs / (1 + freq)) for term, freq in df.items() if term in self._vocabulary}

        # Compute TF-IDF vectors
        vectors = []
        for tf in tf_list:
            vec = [0.0] * len(self._vocabulary)
            for term, count in tf.items():
                if term in self._vocabulary:
                    idx = self._vocabulary[term]
                    tf_val = 1 + math.log(count) if count > 0 else 0
                    vec[idx] = tf_val * self._idf.get(term, 0)
            vectors.append(vec)

        return vectors

    def _reduce_dimensions(self, vectors: list[list[float]]) -> list[list[float]]:
        """Reduce dimensions using random projection (fast, no numpy needed)."""
        if not vectors:
            return []

        input_dim = len(vectors[0])
        output_dim = min(self.dimension, input_dim)

        # Random projection matrix
        import random
        random.seed(42)  # Deterministic
        projection = []
        for _ in range(output_dim):
            row = [random.gauss(0, 1) for _ in range(input_dim)]
            # Normalize
            norm = math.sqrt(sum(x * x for x in row))
            if norm > 0:
                row = [x / norm for x in row]
            projection.append(row)

        # Project vectors
        reduced = []
        for vec in vectors:
            new_vec = []
            for row in projection:
                val = sum(a * b for a, b in zip(vec, row))
                new_vec.append(val)
            reduced.append(new_vec)

        return reduced

    def fit(self, documents: list[str]) -> None:
        """Fit the embedding engine on a corpus of documents."""
        if not documents:
            return

        tfidf_vectors = self._compute_tfidf(documents)
        self._svd_components = self._reduce_dimensions(tfidf_vectors)
        self._fitted = True

    def encode(self, text: str) -> list[float]:
        """Encode a single text into an embedding vector."""
        if not self._vocabulary:
            # No vocabulary — return zero vector
            return [0.0] * self.dimension

        # Compute TF-IDF for this text
        tokens = self._tokenize(text)
        tf = {}
        for token in tokens:
            tf[token] = tf.get(token, 0) + 1

        vec = [0.0] * len(self._vocabulary)
        for term, count in tf.items():
            if term in self._vocabulary:
                idx = self._vocabulary[term]
                tf_val = 1 + math.log(count) if count > 0 else 0
                vec[idx] = tf_val * self._idf.get(term, 0)

        # Reduce dimensions
        if self._svd_components:
            import random
            random.seed(42)
            input_dim = len(vec)
            output_dim = min(self.dimension, input_dim)
            projection = []
            for _ in range(output_dim):
                row = [random.gauss(0, 1) for _ in range(input_dim)]
                norm = math.sqrt(sum(x * x for x in row))
                if norm > 0:
                    row = [x / norm for x in row]
                projection.append(row)

            reduced = []
            for row in projection:
                val = sum(a * b for a, b in zip(vec, row))
                reduced.append(val)
            return reduced

        return vec[:self.dimension]

    def cosine_similarity(self, vec_a: list[float], vec_b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if not vec_a or not vec_b:
            return 0.0

        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot / (norm_a * norm_b)


class SearchService:
    """Semantic search for tracks using lightweight embeddings."""

    def __init__(self, dimension: int = 128):
        self.engine = LightweightEmbeddingEngine(dimension)
        self._track_embeddings = {}  # track_id -> embedding vector
        self._track_data = {}  # track_id -> track metadata

    def _make_document(self, track: dict) -> str:
        """Create a searchable document from track metadata."""
        parts = [
            track.get("title", ""),
            track.get("genre", ""),
            track.get("description", ""),
            track.get("mood", ""),
            track.get("artist_name", ""),
        ]
        return " ".join(p for p in parts if p)

    async def index_tracks(self, db) -> int:
        """Index all tracks in the database. Returns number of tracks indexed."""
        cursor = await db.execute(
            "SELECT t.id, t.title, t.genre, t.description, t.mood, t.audio_url, t.plays, "
            "a.display_name as artist_name, a.username as artist_username "
            "FROM tracks t JOIN artists a ON t.artist_id=a.id"
        )
        rows = await cursor.fetchall()

        if not rows:
            return 0

        # Build documents
        documents = []
        track_ids = []
        for row in rows:
            track = dict(row)
            doc = self._make_document(track)
            documents.append(doc)
            track_ids.append(track["id"])
            self._track_data[track["id"]] = track

        # Fit engine
        self.engine.fit(documents)

        # Generate embeddings for all tracks
        for i, row in enumerate(rows):
            track = dict(row)
            doc = self._make_document(track)
            embedding = self.engine.encode(doc)
            self._track_embeddings[track["id"]] = embedding

        # Store embeddings in database
        for track_id, embedding in self._track_embeddings.items():
            embedding_json = json.dumps(embedding)
            await db.execute(
                "INSERT OR REPLACE INTO track_embeddings (track_id, embedding) VALUES (?, ?)",
                (track_id, embedding_json)
            )

        return len(rows)

    async def load_embeddings(self, db) -> int:
        """Load pre-computed embeddings from database."""
        cursor = await db.execute(
            "SELECT te.track_id, te.embedding, t.title, t.genre, t.description, t.mood, "
            "t.audio_url, t.plays, a.display_name as artist_name, a.username as artist_username "
            "FROM track_embeddings te "
            "JOIN tracks t ON te.track_id=t.id "
            "JOIN artists a ON t.artist_id=a.id"
        )
        rows = await cursor.fetchall()

        for row in rows:
            track = dict(row)
            track_id = track["id"]
            embedding = json.loads(row["embedding"])
            self._track_embeddings[track_id] = embedding
            self._track_data[track_id] = track

        return len(rows)

    async def search_tracks(self, query: str, db, limit: int = 20) -> list[dict]:
        """Search tracks by semantic similarity."""
        if not self._track_embeddings:
            # Try to load from DB
            count = await self.load_embeddings(db)
            if count == 0:
                # No embeddings — index tracks first
                await self.index_tracks(db)

        if not self._track_embeddings:
            return []

        # Encode query
        query_embedding = self.engine.encode(query)

        # Score all tracks by cosine similarity
        results = []
        for track_id, track_embedding in self._track_embeddings.items():
            score = self.engine.cosine_similarity(query_embedding, track_embedding)
            track_data = self._track_data.get(track_id, {})
            results.append({
                "track_id": track_id,
                "title": track_data.get("title", ""),
                "artist_name": track_data.get("artist_name", ""),
                "artist_username": track_data.get("artist_username", ""),
                "genre": track_data.get("genre", ""),
                "mood": track_data.get("mood", ""),
                "description": track_data.get("description", ""),
                "audio_url": track_data.get("audio_url", ""),
                "plays": track_data.get("plays", 0),
                "score": round(score, 4),
            })

        # Sort by similarity score
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    async def find_similar_tracks(self, track_id: int, db, limit: int = 10) -> list[dict]:
        """Find tracks similar to a given track."""
        if not self._track_embeddings:
            await self.load_embeddings(db)

        if track_id not in self._track_embeddings:
            return []

        target_embedding = self._track_embeddings[track_id]

        results = []
        for tid, embedding in self._track_embeddings.items():
            if tid == track_id:
                continue
            score = self.engine.cosine_similarity(target_embedding, embedding)
            track_data = self._track_data.get(tid, {})
            results.append({
                "track_id": tid,
                "title": track_data.get("title", ""),
                "artist_name": track_data.get("artist_name", ""),
                "artist_username": track_data.get("artist_username", ""),
                "genre": track_data.get("genre", ""),
                "audio_url": track_data.get("audio_url", ""),
                "plays": track_data.get("plays", 0),
                "score": round(score, 4),
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]


# Singleton
search_service = SearchService(dimension=128)
