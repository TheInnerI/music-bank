"""
Music Bank — Database layer
SQLite + aiosqlite for async DB operations
"""
import aiosqlite
import os
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "music_bank.db"


async def get_db() -> aiosqlite.Connection:
    """Get async database connection."""
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db():
    """Initialize database schema."""
    db = await get_db()
    try:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS artists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                display_name TEXT NOT NULL,
                bio TEXT DEFAULT '',
                avatar_url TEXT DEFAULT '',
                genre TEXT DEFAULT '',
                location TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_verified INTEGER DEFAULT 0,
                total_plays INTEGER DEFAULT 0,
                total_earnings_cents INTEGER DEFAULT 0,
                balance_cents INTEGER DEFAULT 0,
                -- Multi-rail balances
                balance_usdc REAL DEFAULT 0,
                balance_mio REAL DEFAULT 0,
                balance_btc REAL DEFAULT 0,
                -- Stripe Connect
                stripe_account_id TEXT DEFAULT '',
                stripe_onboarding_complete INTEGER DEFAULT 0,
                -- Crypto payout addresses
                eth_wallet_address TEXT DEFAULT '',
                base_wallet_address TEXT DEFAULT '',
                btc_address TEXT DEFAULT '',
                cashapp_cashtag TEXT DEFAULT '',
                -- Profile enrichment: platform links
                website_url TEXT DEFAULT '',
                soundcloud_url TEXT DEFAULT '',
                bandcamp_url TEXT DEFAULT '',
                instagram_url TEXT DEFAULT '',
                twitter_url TEXT DEFAULT '',
                tiktok_url TEXT DEFAULT '',
                -- Vector embedding cache
                profile_embedding BLOB DEFAULT '',
                profile_embedding_updated TIMESTAMP DEFAULT NULL,
                -- Graph position cache
                graph_x REAL DEFAULT 0,
                graph_y REAL DEFAULT 0,
                graph_cluster TEXT DEFAULT '',
                -- Forever earnings tracking
                lifetime_deposits_cents INTEGER DEFAULT 0,
                lifetime_deposits_usdc REAL DEFAULT 0,
                lifetime_deposits_mio REAL DEFAULT 0,
                total_fans INTEGER DEFAULT 0,
                -- Tier (free forever, pro = analytics, label = multi-artist)
                tier TEXT DEFAULT 'free'
            );

            CREATE TABLE IF NOT EXISTS tracks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                artist_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                genre TEXT DEFAULT '',
                duration_seconds INTEGER DEFAULT 0,
                audio_url TEXT NOT NULL,
                cover_url TEXT DEFAULT '',
                isrc TEXT DEFAULT '',
                lyrics TEXT DEFAULT '',
                bpm INTEGER DEFAULT 0,
                key_signature TEXT DEFAULT '',
                mood TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                plays INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                deposits INTEGER DEFAULT 0,
                earnings_cents INTEGER DEFAULT 0,
                is_published INTEGER DEFAULT 0,
                -- License & copyright
                license_type TEXT DEFAULT 'all_rights_reserved',
                ai_level TEXT DEFAULT 'fully_human',
                ai_tools TEXT DEFAULT '[]',  -- JSON array of tool names
                sync_available INTEGER DEFAULT 0,
                sync_price TEXT DEFAULT '',
                copyright_notice TEXT DEFAULT '',
                upc TEXT DEFAULT '',
                FOREIGN KEY (artist_id) REFERENCES artists(id)
            );

            CREATE TABLE IF NOT EXISTS plays (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                track_id INTEGER NOT NULL,
                listener_id INTEGER DEFAULT NULL,
                played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                duration_listened INTEGER DEFAULT 0,
                source TEXT DEFAULT 'direct',
                FOREIGN KEY (track_id) REFERENCES tracks(id)
            );

            CREATE TABLE IF NOT EXISTS likes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                track_id INTEGER NOT NULL,
                artist_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(track_id, artist_id),
                FOREIGN KEY (track_id) REFERENCES tracks(id),
                FOREIGN KEY (artist_id) REFERENCES artists(id)
            );

            CREATE TABLE IF NOT EXISTS follows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                follower_id INTEGER NOT NULL,
                followed_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(follower_id, followed_id),
                FOREIGN KEY (follower_id) REFERENCES artists(id),
                FOREIGN KEY (followed_id) REFERENCES artists(id)
            );

            CREATE TABLE IF NOT EXISTS deposits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                artist_id INTEGER NOT NULL,
                track_id INTEGER NOT NULL,
                amount_cents INTEGER NOT NULL,
                deposit_type TEXT DEFAULT 'fan_support',
                message TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (artist_id) REFERENCES artists(id),
                FOREIGN KEY (track_id) REFERENCES tracks(id)
            );

            CREATE TABLE IF NOT EXISTS bank_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                artist_id INTEGER NOT NULL,
                amount_cents INTEGER NOT NULL,
                transaction_type TEXT NOT NULL,
                description TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (artist_id) REFERENCES artists(id)
            );

            CREATE TABLE IF NOT EXISTS discovery_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                track_id INTEGER NOT NULL,
                signal_type TEXT NOT NULL,
                score REAL DEFAULT 0.0,
                computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (track_id) REFERENCES tracks(id)
            );

            CREATE INDEX IF NOT EXISTS idx_tracks_artist ON tracks(artist_id);
            CREATE INDEX IF NOT EXISTS idx_tracks_genre ON tracks(genre);
            CREATE INDEX IF NOT EXISTS idx_tracks_plays ON tracks(plays DESC);
            CREATE INDEX IF NOT EXISTS idx_tracks_created ON tracks(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_plays_track ON plays(track_id);
            CREATE INDEX IF NOT EXISTS idx_likes_track ON likes(track_id);
            CREATE INDEX IF NOT EXISTS idx_deposits_artist ON deposits(artist_id);
            CREATE INDEX IF NOT EXISTS idx_discovery_track ON discovery_signals(track_id);

            -- ============================================
            -- MULTI-RAIL PAYMENT TABLES
            -- ============================================

            -- Artist payout preferences (how they want to get paid)
            CREATE TABLE IF NOT EXISTS artist_payout_methods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                artist_id INTEGER NOT NULL,
                method_type TEXT NOT NULL,  -- 'stripe_connect', 'coinbase_usdc', 'bitcoin', 'cashapp'
                is_default INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                -- Stripe Connect
                stripe_account_id TEXT DEFAULT '',
                stripe_onboarding_complete INTEGER DEFAULT 0,
                -- Coinbase / USDC on Base
                eth_wallet_address TEXT DEFAULT '',
                base_wallet_address TEXT DEFAULT '',
                -- Bitcoin
                btc_address TEXT DEFAULT '',
                -- Cash App
                cashapp_cashtag TEXT DEFAULT '',
                cashapp_country TEXT DEFAULT 'US',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (artist_id) REFERENCES artists(id)
            );

            -- Payment rails for deposits (fan → artist)
            CREATE TABLE IF NOT EXISTS payment_deposits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                artist_id INTEGER NOT NULL,
                track_id INTEGER DEFAULT NULL,
                fan_artist_id INTEGER DEFAULT NULL,
                amount_cents INTEGER NOT NULL,  -- Always stored in cents equivalent
                amount_usdc REAL DEFAULT 0,      -- USDC amount if crypto
                amount_mio REAL DEFAULT 0,       -- $MIO token amount
                payment_rail TEXT NOT NULL,      -- 'stripe', 'usdc_base', 'virtuals_mio'
                -- Stripe fields
                stripe_payment_intent_id TEXT DEFAULT '',
                stripe_charge_id TEXT DEFAULT '',
                -- Base / USDC fields
                base_tx_hash TEXT DEFAULT '',
                base_block_number INTEGER DEFAULT 0,
                usdc_contract_address TEXT DEFAULT '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
                from_wallet_address TEXT DEFAULT '',
                -- Virtuals fields
                virtuals_tx_hash TEXT DEFAULT '',
                mio_token_amount REAL DEFAULT 0,
                -- Status
                status TEXT DEFAULT 'pending',   -- 'pending', 'completed', 'failed', 'refunded'
                platform_fee_cents INTEGER DEFAULT 0,
                artist_payout_cents INTEGER NOT NULL,
                message TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP DEFAULT NULL,
                FOREIGN KEY (artist_id) REFERENCES artists(id),
                FOREIGN KEY (track_id) REFERENCES tracks(id)
            );

            -- Artist payout requests
            CREATE TABLE IF NOT EXISTS payout_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                artist_id INTEGER NOT NULL,
                amount_cents INTEGER NOT NULL,
                payout_method TEXT NOT NULL,     -- 'stripe_connect', 'coinbase_usdc', 'bitcoin', 'cashapp'
                payout_method_id INTEGER DEFAULT NULL,
                status TEXT DEFAULT 'pending',   -- 'pending', 'processing', 'completed', 'failed'
                -- Stripe
                stripe_transfer_id TEXT DEFAULT '',
                -- Coinbase / USDC
                coinbase_transfer_id TEXT DEFAULT '',
                usdc_amount REAL DEFAULT 0,
                destination_address TEXT DEFAULT '',
                -- Bitcoin
                btc_tx_hash TEXT DEFAULT '',
                btc_amount REAL DEFAULT 0,
                -- Cash App
                cashapp_transfer_id TEXT DEFAULT '',
                -- Meta
                failure_reason TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP DEFAULT NULL,
                FOREIGN KEY (artist_id) REFERENCES artists(id)
            );

            -- Platform fee tracking
            CREATE TABLE IF NOT EXISTS platform_fees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deposit_id INTEGER NOT NULL,
                fee_cents INTEGER NOT NULL,
                fee_type TEXT DEFAULT 'platform',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (deposit_id) REFERENCES payment_deposits(id)
            );

            CREATE INDEX IF NOT EXISTS idx_deposits_rail ON payment_deposits(payment_rail);
            CREATE INDEX IF NOT EXISTS idx_deposits_status ON payment_deposits(status);
            CREATE INDEX IF NOT EXISTS idx_deposits_artist ON payment_deposits(artist_id);
            CREATE INDEX IF NOT EXISTS idx_payouts_artist ON payout_requests(artist_id);
            CREATE INDEX IF NOT EXISTS idx_payouts_status ON payout_requests(status);
            CREATE INDEX IF NOT EXISTS idx_payout_methods_artist ON artist_payout_methods(artist_id);

            -- ============================================
            -- GRAPH + VECTOR + PROFILE TABLES (v0.2)
            -- ============================================

            -- Artist platform links (YouTube, Spotify, Apple Music, etc.)
            CREATE TABLE IF NOT EXISTS artist_platform_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                artist_id INTEGER NOT NULL,
                platform TEXT NOT NULL,
                url TEXT NOT NULL,
                platform_id TEXT DEFAULT '',
                is_verified INTEGER DEFAULT 0,
                follower_count INTEGER DEFAULT 0,
                last_synced TIMESTAMP DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (artist_id) REFERENCES artists(id),
                UNIQUE(artist_id, platform)
            );

            -- Track embeddings for semantic search
            CREATE TABLE IF NOT EXISTS track_embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                track_id INTEGER NOT NULL,
                embedding BLOB NOT NULL,
                embedding_model TEXT DEFAULT 'all-MiniLM-L6-v2',
                dimension INTEGER DEFAULT 384,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (track_id) REFERENCES tracks(id),
                UNIQUE(track_id)
            );

            -- Graph edges (connections between users)
            CREATE TABLE IF NOT EXISTS graph_edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                target_id INTEGER NOT NULL,
                edge_type TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_id) REFERENCES artists(id),
                FOREIGN KEY (target_id) REFERENCES artists(id),
                UNIQUE(source_id, target_id, edge_type)
            );

            -- Fan behavior vectors (compressed representation of who they support)
            CREATE TABLE IF NOT EXISTS fan_vectors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                artist_id INTEGER NOT NULL,
                vector BLOB NOT NULL,
                dimension INTEGER DEFAULT 384,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (artist_id) REFERENCES artists(id),
                UNIQUE(artist_id)
            );

            -- Compressed artist collection vectors (all tracks + links → single vector)
            CREATE TABLE IF NOT EXISTS artist_collection_vectors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                artist_id INTEGER NOT NULL,
                collection_vector BLOB NOT NULL,
                source_urls TEXT DEFAULT '[]',
                dimension INTEGER DEFAULT 384,
                compression_ratio REAL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (artist_id) REFERENCES artists(id),
                UNIQUE(artist_id)
            );

            -- Forever earnings ledger (immutable record)
            CREATE TABLE IF NOT EXISTS earnings_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                artist_id INTEGER NOT NULL,
                track_id INTEGER DEFAULT NULL,
                amount_cents INTEGER DEFAULT 0,
                amount_usdc REAL DEFAULT 0,
                amount_mio REAL DEFAULT 0,
                earning_type TEXT NOT NULL,
                source TEXT DEFAULT '',
                fan_id INTEGER DEFAULT NULL,
                description TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (artist_id) REFERENCES artists(id)
            );

            -- Collaborations between artists
            CREATE TABLE IF NOT EXISTS collaborations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                track_id INTEGER NOT NULL,
                artist_id INTEGER NOT NULL,
                role TEXT DEFAULT 'primary',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (track_id) REFERENCES tracks(id),
                FOREIGN KEY (artist_id) REFERENCES artists(id),
                UNIQUE(track_id, artist_id)
            );

            -- Platform sync status
            CREATE TABLE IF NOT EXISTS platform_sync (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                artist_id INTEGER NOT NULL,
                platform TEXT NOT NULL,
                last_sync TIMESTAMP DEFAULT NULL,
                sync_status TEXT DEFAULT 'pending',
                sync_data TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (artist_id) REFERENCES artists(id),
                UNIQUE(artist_id, platform)
            );

            CREATE INDEX IF NOT EXISTS idx_platform_links_artist ON artist_platform_links(artist_id);
            CREATE INDEX IF NOT EXISTS idx_track_embeddings_track ON track_embeddings(track_id);
            CREATE INDEX IF NOT EXISTS idx_graph_edges_source ON graph_edges(source_id);
            CREATE INDEX IF NOT EXISTS idx_graph_edges_target ON graph_edges(target_id);
            CREATE INDEX IF NOT EXISTS idx_graph_edges_type ON graph_edges(edge_type);
            CREATE INDEX IF NOT EXISTS idx_earnings_artist ON earnings_ledger(artist_id);
            CREATE INDEX IF NOT EXISTS idx_earnings_created ON earnings_ledger(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_fan_vectors ON fan_vectors(artist_id);
            CREATE INDEX IF NOT EXISTS idx_collaborations_track ON collaborations(track_id);
            CREATE INDEX IF NOT EXISTS idx_collaborations_artist ON collaborations(artist_id);

            -- ============================================
            -- LEGAL + LICENSING TABLES (v0.2)
            -- ============================================

            -- Track fingerprints (for ownership proof)
            CREATE TABLE IF NOT EXISTS track_fingerprints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                track_id INTEGER NOT NULL,
                content_hash TEXT NOT NULL,
                perceptual_hash TEXT NOT NULL,
                file_size INTEGER DEFAULT 0,
                format TEXT DEFAULT 'unknown',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (track_id) REFERENCES tracks(id),
                UNIQUE(track_id)
            );

            -- Track provenance (timestamped proof of creation)
            CREATE TABLE IF NOT EXISTS track_provenance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                track_id INTEGER NOT NULL,
                data TEXT NOT NULL,  -- JSON: full provenance record
                provenance_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (track_id) REFERENCES tracks(id),
                UNIQUE(track_id)
            );

            -- Royalty splits for collaborative tracks
            CREATE TABLE IF NOT EXISTS royalty_splits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                track_id INTEGER NOT NULL,
                artist_id INTEGER NOT NULL,
                percentage REAL NOT NULL,
                role TEXT DEFAULT 'contributor',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (track_id) REFERENCES tracks(id),
                FOREIGN KEY (artist_id) REFERENCES artists(id),
                UNIQUE(track_id, artist_id)
            );

            -- Sample clearance tracking
            CREATE TABLE IF NOT EXISTS track_samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                track_id INTEGER NOT NULL,
                original_title TEXT DEFAULT '',
                original_artist TEXT DEFAULT '',
                original_label TEXT DEFAULT '',
                clearance_status TEXT DEFAULT 'not_required',
                clearance_notes TEXT DEFAULT '',
                license_fee TEXT DEFAULT '',
                royalty_percentage REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (track_id) REFERENCES tracks(id)
            );

            -- DMCA reports
            CREATE TABLE IF NOT EXISTS dmca_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                complainant_name TEXT NOT NULL,
                complainant_email TEXT NOT NULL,
                original_work TEXT DEFAULT '',
                infringing_url TEXT DEFAULT '',
                statement_good_faith TEXT DEFAULT '',
                statement_accuracy TEXT DEFAULT '',
                signature TEXT DEFAULT '',
                status TEXT DEFAULT 'pending',
                resolution TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP DEFAULT NULL
            );

            -- Licensing deals
            CREATE TABLE IF NOT EXISTS licensing_deals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                track_id INTEGER NOT NULL,
                licensee_name TEXT DEFAULT '',
                licensee_email TEXT DEFAULT '',
                license_type TEXT DEFAULT 'sync',
                intended_use TEXT DEFAULT '',
                budget_range TEXT DEFAULT '',
                status TEXT DEFAULT 'inquiry',
                platform_fee_cents INTEGER DEFAULT 0,
                artist_payout_cents INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP DEFAULT NULL,
                FOREIGN KEY (track_id) REFERENCES tracks(id)
            );

            -- AI tool usage per track
            CREATE TABLE IF NOT EXISTS track_ai_tools (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                track_id INTEGER NOT NULL,
                tool_name TEXT NOT NULL,
                tool_type TEXT DEFAULT '',
                version TEXT DEFAULT '',
                prompt_text TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (track_id) REFERENCES tracks(id)
            );

            CREATE INDEX IF NOT EXISTS idx_fingerprints_track ON track_fingerprints(track_id);
            CREATE INDEX IF NOT EXISTS idx_fingerprints_hash ON track_fingerprints(content_hash);
            CREATE INDEX IF NOT EXISTS idx_provenance_track ON track_provenance(track_id);
            CREATE INDEX IF NOT EXISTS idx_royalty_splits_track ON royalty_splits(track_id);
            CREATE INDEX IF NOT EXISTS idx_samples_track ON track_samples(track_id);
            CREATE INDEX IF NOT EXISTS idx_dmca_status ON dmca_reports(status);
            CREATE INDEX IF NOT EXISTS idx_licensing_track ON licensing_deals(track_id);
            CREATE INDEX IF NOT EXISTS idx_ai_tools_track ON track_ai_tools(track_id);

            -- Agent evaluations
            CREATE TABLE IF NOT EXISTS agent_evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                track_id INTEGER,
                eval_type TEXT DEFAULT 'standard_eval',
                score INTEGER DEFAULT 0,
                feedback TEXT DEFAULT '',
                status TEXT DEFAULT 'pending',
                raw_result TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (track_id) REFERENCES tracks(id)
            );

            -- Password resets
            CREATE TABLE IF NOT EXISTS password_resets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                artist_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                used INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (artist_id) REFERENCES artists(id)
            );

            -- Import history
            CREATE TABLE IF NOT EXISTS import_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                artist_id INTEGER NOT NULL,
                platform TEXT NOT NULL,
                items_imported INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                error_message TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (artist_id) REFERENCES artists(id)
            );

            CREATE INDEX IF NOT EXISTS idx_import_history_artist ON import_history(artist_id);
        """)

        await db.commit()
    finally:
        await db.close()


async def seed_demo_data():
    """Seed demo data for MVP testing."""
    db = await get_db()
    try:
        # Check if already seeded
        cursor = await db.execute("SELECT COUNT(*) FROM artists")
        row = await cursor.fetchone()
        if row[0] > 0:
            return

        import bcrypt
        pw = bcrypt.hashpw(b"demo1234", bcrypt.gensalt()).decode()

        # Demo artists
        artists = [
            ("luna_echo", "luna@demo.com", pw, "Luna Echo", "Electronic dreamscape producer from Berlin", "Electronic", "Berlin"),
            ("marcus_blues", "marcus@demo.com", pw, "Marcus Blues", "Soulful blues guitarist keeping it raw", "Blues", "Chicago"),
            ("yuki_beats", "yuki@demo.com", pw, "Yuki Beats", "Lo-fi hip hop from Tokyo nights", "Lo-fi", "Tokyo"),
            ("sofia_strings", "sofia@demo.com", pw, "Sofía Strings", "Classical crossover with Latin fire", "Classical", "Buenos Aires"),
            ("dust_bunny", "dust@demo.com", pw, "Dust Bunny", "Indie folk that sounds like a campfire confession", "Indie Folk", "Portland"),
        ]

        for a in artists:
            await db.execute(
                "INSERT INTO artists (username, email, password_hash, display_name, bio, genre, location) VALUES (?, ?, ?, ?, ?, ?, ?)",
                a
            )

        # Seed platform links for demo artists
        platform_links = [
            (1, "youtube", "https://www.youtube.com/@innerinetwork/", "@innerinetwork", 1, 1000),
            (1, "spotify", "https://open.spotify.com/artist/luna_echo", "luna_echo", 1, 500),
            (1, "apple_music", "https://music.apple.com/artist/luna_echo", "", 0, 200),
            (1, "soundcloud", "https://soundcloud.com/luna_echo", "", 0, 300),
            (1, "bandcamp", "https://lunaecho.bandcamp.com", "", 0, 150),
            (2, "youtube", "https://www.youtube.com/@marcusblues/", "@marcusblues", 1, 800),
            (2, "spotify", "https://open.spotify.com/artist/marcus_blues", "marcus_blues", 1, 400),
            (3, "youtube", "https://www.youtube.com/@yukibeats/", "@yukibeats", 1, 2000),
            (3, "spotify", "https://open.spotify.com/artist/yuki_beats", "yuki_beats", 1, 1500),
            (3, "soundcloud", "https://soundcloud.com/yuki_beats", "", 1, 800),
            (4, "youtube", "https://www.youtube.com/@sofiastrings/", "@sofiastrings", 1, 600),
            (4, "spotify", "https://open.spotify.com/artist/sofia_strings", "sofia_strings", 1, 350),
            (5, "youtube", "https://www.youtube.com/@dustbunnyfolk/", "@dustbunnyfolk", 1, 400),
            (5, "bandcamp", "https://dustbunny.bandcamp.com", "", 1, 250),
        ]

        for pl in platform_links:
            await db.execute(
                "INSERT INTO artist_platform_links (artist_id, platform, url, platform_id, is_verified, follower_count) VALUES (?, ?, ?, ?, ?, ?)",
                pl
            )

        # Demo tracks
        tracks = [
            (1, "Neon Rain", "Late night city vibes", "Electronic", 214, "/static/audio/demo1.mp3", "", "", "", 128, "Am", "atmospheric"),
            (1, "Crystal Memory", "A journey through light", "Electronic", 187, "/static/audio/demo2.mp3", "", "", "", 110, "Cm", "euphoric"),
            (2, "Delta Ghost", "Mississippi delta meets Chicago south side", "Blues", 245, "/static/audio/demo3.mp3", "", "", "", 92, "Em", "raw"),
            (2, "Whiskey Prayer", "For the ones who stayed", "Blues", 198, "/static/audio/demo4.mp3", "", "", "", 85, "Gm", "soulful"),
            (3, "Shibuya Nights", "Rain on neon signs", "Lo-fi", 176, "/static/audio/demo5.mp3", "", "", "", 75, "Dm", "chill"),
            (3, "Matcha Dreams", "Soft focus morning", "Lo-fi", 162, "/static/audio/demo6.mp3", "", "", "", 70, "Fm", "peaceful"),
            (4, "Tango Noir", "Classical strings meet dark tango", "Classical", 267, "/static/audio/demo7.mp3", "", "", "", 120, "Bm", "dramatic"),
            (4, "Patagonia Wind", "The sound of open spaces", "Classical", 223, "/static/audio/demo8.mp3", "", "", "", 95, "Am", "expansive"),
            (5, "Pine Needle Crown", "Songs from the forest floor", "Indie Folk", 201, "/static/audio/demo9.mp3", "", "", "", 100, "C", "warm"),
            (5, "Rust & Gold", "Growing old beautifully", "Indie Folk", 189, "/static/audio/demo10.mp3", "", "", "", 88, "G", "nostalgic"),
        ]

        for t in tracks:
            await db.execute(
                "INSERT INTO tracks (artist_id, title, description, genre, duration_seconds, audio_url, cover_url, isrc, lyrics, bpm, key_signature, mood, is_published) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,1)",
                t
            )

        # Seed some plays and likes for discovery algorithm
        import random
        for track_id in range(1, 11):
            plays = random.randint(50, 5000)
            likes = random.randint(10, int(plays * 0.3))
            await db.execute("UPDATE tracks SET plays=?, likes=? WHERE id=?", (plays, likes, track_id))

        # Update artist totals
        for artist_id in range(1, 6):
            await db.execute(
                "UPDATE artists SET total_plays=(SELECT COALESCE(SUM(plays),0) FROM tracks WHERE artist_id=?) WHERE id=?",
                (artist_id, artist_id)
            )

        await db.commit()
    finally:
        await db.close()
