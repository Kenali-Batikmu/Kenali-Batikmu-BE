-- ============================================================================
-- Kenali Batikmu - Skema Database (SQLite) - versi 2 (lihat SCHEMA_VERSION di db.py)
-- Waktu disimpan sebagai teks ISO-8601 UTC (contoh: 2026-10-10T05:30:00Z).
-- Boolean disimpan sebagai INTEGER 0/1.
-- PRAGMA foreign_keys bersifat per-koneksi: aktifkan lagi di setiap koneksi
-- aplikasi (sqflite: onConfigure -> db.execute('PRAGMA foreign_keys = ON')).
-- ============================================================================

PRAGMA foreign_keys = ON;

-- 1. users ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,
    email           TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    phone           TEXT,
    password_hash   TEXT    NOT NULL,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    lockout_until   TEXT,
    created_at      TEXT    NOT NULL,
    updated_at      TEXT    NOT NULL
);

-- 2. batik_motifs -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS batik_motifs (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    name              TEXT    NOT NULL,
    slug              TEXT    NOT NULL UNIQUE,
    origin_region     TEXT    NOT NULL,
    short_description TEXT    NOT NULL,
    thumbnail_url     TEXT,
    ml_class_index    INTEGER NOT NULL UNIQUE CHECK (ml_class_index >= 0)
);

-- 3. modules ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS modules (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    motif_id      INTEGER NOT NULL REFERENCES batik_motifs (id),
    title         TEXT    NOT NULL,
    description   TEXT    NOT NULL,
    cover_image   TEXT,
    video_url     TEXT,
    passing_score INTEGER NOT NULL DEFAULT 70 CHECK (passing_score BETWEEN 0 AND 100),
    order_no      INTEGER NOT NULL UNIQUE
);

-- 4. module_contents --------------------------------------------------------
CREATE TABLE IF NOT EXISTS module_contents (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id INTEGER NOT NULL REFERENCES modules (id) ON DELETE CASCADE,
    pillar    TEXT    NOT NULL CHECK (pillar IN ('sejarah_filosofi', 'karakteristik', 'galeri')),
    title     TEXT    NOT NULL,
    body      TEXT    NOT NULL,
    badge     TEXT,
    order_no  INTEGER NOT NULL,
    UNIQUE (module_id, pillar, order_no)
);

-- 5. module_gallery_images --------------------------------------------------
CREATE TABLE IF NOT EXISTS module_gallery_images (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id INTEGER NOT NULL REFERENCES modules (id) ON DELETE CASCADE,
    image_url TEXT,
    caption   TEXT,
    order_no  INTEGER NOT NULL,
    UNIQUE (module_id, order_no)
);

-- 6. quiz_questions ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS quiz_questions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id      INTEGER NOT NULL REFERENCES modules (id) ON DELETE CASCADE,
    question       TEXT    NOT NULL,
    option_a       TEXT    NOT NULL,
    option_b       TEXT    NOT NULL,
    option_c       TEXT    NOT NULL,
    option_d       TEXT    NOT NULL,
    correct_option TEXT    NOT NULL CHECK (correct_option IN ('A', 'B', 'C', 'D')),
    explanation    TEXT
);

-- 7. user_module_progress ---------------------------------------------------
CREATE TABLE IF NOT EXISTS user_module_progress (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL REFERENCES users (id)   ON DELETE CASCADE,
    module_id        INTEGER NOT NULL REFERENCES modules (id) ON DELETE CASCADE,
    status           TEXT    NOT NULL DEFAULT 'not_started'
                     CHECK (status IN ('not_started', 'in_progress', 'completed')),
    progress_percent INTEGER NOT NULL DEFAULT 0 CHECK (progress_percent BETWEEN 0 AND 100),
    history_done     INTEGER NOT NULL DEFAULT 0 CHECK (history_done   IN (0, 1)),
    character_done   INTEGER NOT NULL DEFAULT 0 CHECK (character_done IN (0, 1)),
    gallery_done     INTEGER NOT NULL DEFAULT 0 CHECK (gallery_done   IN (0, 1)),
    quiz_done        INTEGER NOT NULL DEFAULT 0 CHECK (quiz_done      IN (0, 1)),
    practice_done    INTEGER NOT NULL DEFAULT 0 CHECK (practice_done  IN (0, 1)),
    completed_at     TEXT,
    last_accessed_at TEXT    NOT NULL,
    UNIQUE (user_id, module_id)
);

-- 8. quiz_attempts ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS quiz_attempts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL REFERENCES users (id)   ON DELETE CASCADE,
    module_id    INTEGER NOT NULL REFERENCES modules (id) ON DELETE CASCADE,
    score        INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),
    passed       INTEGER NOT NULL CHECK (passed IN (0, 1)),
    attempted_at TEXT    NOT NULL
);

-- 9. quiz_attempt_answers ---------------------------------------------------
CREATE TABLE IF NOT EXISTS quiz_attempt_answers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id      INTEGER NOT NULL REFERENCES quiz_attempts (id)  ON DELETE CASCADE,
    question_id     INTEGER NOT NULL REFERENCES quiz_questions (id) ON DELETE CASCADE,
    selected_option TEXT    NOT NULL CHECK (selected_option IN ('A', 'B', 'C', 'D')),
    is_correct      INTEGER NOT NULL CHECK (is_correct IN (0, 1)),
    UNIQUE (attempt_id, question_id)
);

-- 10. scans -----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS scans (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id           INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    scan_type         TEXT    NOT NULL CHECK (scan_type IN ('universal', 'kuismu')),
    module_id         INTEGER REFERENCES modules (id),
    image_path        TEXT,
    top_motif_id      INTEGER REFERENCES batik_motifs (id),
    confidence        REAL CHECK (confidence BETWEEN 0 AND 1),
    fit_score         REAL CHECK (fit_score  BETWEEN 0 AND 1),
    passed            INTEGER CHECK (passed IN (0, 1)),
    inference_time_ms INTEGER,
    created_at        TEXT    NOT NULL,
    CHECK (scan_type = 'universal' OR module_id IS NOT NULL)
);

-- 11. scan_probabilities ----------------------------------------------------
CREATE TABLE IF NOT EXISTS scan_probabilities (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id     INTEGER NOT NULL REFERENCES scans (id)        ON DELETE CASCADE,
    motif_id    INTEGER NOT NULL REFERENCES batik_motifs (id),
    probability REAL    NOT NULL CHECK (probability BETWEEN 0 AND 1),
    UNIQUE (scan_id, motif_id)
);

-- 12. password_resets -------------------------------------------------------
-- OTP lupa kata sandi. Yang disimpan hanya HMAC dari OTP (bukan OTP-nya).
-- Alur: forgot-password (buat OTP) -> verify-otp (OTP benar -> reset_token) ->
--       reset-password (reset_token + sandi baru -> used_at diisi).
CREATE TABLE IF NOT EXISTS password_resets (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    otp_hash         TEXT    NOT NULL,
    attempts         INTEGER NOT NULL DEFAULT 0,
    verified         INTEGER NOT NULL DEFAULT 0 CHECK (verified IN (0, 1)),
    reset_token_hash TEXT,
    expires_at       TEXT    NOT NULL,
    used_at          TEXT,
    created_at       TEXT    NOT NULL
);

-- Indeks untuk query yang sering dipakai ------------------------------------
CREATE INDEX IF NOT EXISTS idx_modules_motif        ON modules (motif_id);
CREATE INDEX IF NOT EXISTS idx_contents_module      ON module_contents (module_id, pillar, order_no);
CREATE INDEX IF NOT EXISTS idx_questions_module     ON quiz_questions (module_id);
CREATE INDEX IF NOT EXISTS idx_attempts_user_module ON quiz_attempts (user_id, module_id, attempted_at);
CREATE INDEX IF NOT EXISTS idx_scans_user           ON scans (user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_scanprob_scan        ON scan_probabilities (scan_id);
CREATE INDEX IF NOT EXISTS idx_scans_module         ON scans (user_id, module_id, scan_type);
CREATE INDEX IF NOT EXISTS idx_resets_user          ON password_resets (user_id, created_at);
