import aiosqlite
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage", "mcf.db")

async def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS cases (
                id TEXT PRIMARY KEY,
                case_number TEXT NOT NULL UNIQUE,
                child_name TEXT NOT NULL,
                child_age INTEGER,
                last_seen_date TEXT,
                last_seen_place TEXT,
                description TEXT,
                officer_name TEXT,
                officer_contact TEXT,
                status TEXT DEFAULT 'active',
                reference_photo TEXT,
                face_embedding BLOB,
                total_matches INTEGER DEFAULT 0,
                videos_analyzed INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                synced INTEGER DEFAULT 0,
                last_synced_at TEXT
            )
        ''')
        await db.execute('CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status)')
        await db.execute('CREATE INDEX IF NOT EXISTS idx_cases_created_at ON cases(created_at)')

        await db.execute('''
            CREATE TABLE IF NOT EXISTS matches (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                video_source TEXT NOT NULL,
                source_type TEXT DEFAULT 'upload',
                timestamp_seconds REAL NOT NULL,
                timestamp_display TEXT,
                frame_number INTEGER,
                confidence_score REAL NOT NULL,
                bbox_x1 REAL,
                bbox_y1 REAL,
                bbox_x2 REAL,
                bbox_y2 REAL,
                screenshot_local TEXT,
                screenshot_cloud TEXT,
                sam_mask_applied INTEGER DEFAULT 0,
                camera_id TEXT,
                is_confirmed INTEGER DEFAULT 0,
                is_false_positive INTEGER DEFAULT 0,
                investigator_note TEXT,
                detected_at TEXT DEFAULT (datetime('now')),
                synced INTEGER DEFAULT 0,
                last_synced_at TEXT,
                FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
            )
        ''')
        await db.execute('CREATE INDEX IF NOT EXISTS idx_matches_case_id ON matches(case_id)')
        await db.execute('CREATE INDEX IF NOT EXISTS idx_matches_confidence ON matches(confidence_score DESC)')
        await db.execute('CREATE INDEX IF NOT EXISTS idx_matches_detected_at ON matches(detected_at)')
        await db.execute('CREATE INDEX IF NOT EXISTS idx_matches_source_type ON matches(source_type)')

        await db.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                job_type TEXT NOT NULL,
                video_path TEXT,
                rtsp_url TEXT,
                status TEXT DEFAULT 'queued',
                progress_pct INTEGER DEFAULT 0,
                frames_total INTEGER,
                frames_done INTEGER DEFAULT 0,
                error_message TEXT,
                started_at TEXT,
                completed_at TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (case_id) REFERENCES cases(id)
            )
        ''')
        # Enable WAL mode for concurrent reads/writes
        await db.execute('PRAGMA journal_mode=WAL')
        await db.commit()

async def get_db_connection():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db
