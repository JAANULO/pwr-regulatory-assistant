CREATE TABLE IF NOT EXISTS pytania (
    id          SERIAL PRIMARY KEY,
    pytanie     TEXT NOT NULL,
    tytul       TEXT,
    podobienstwo REAL,
    odpowiedz   TEXT,
    baza        TEXT DEFAULT 'studia',
    czas        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS feedback (
    id          SERIAL PRIMARY KEY,
    pytanie_id  INTEGER REFERENCES pytania(id),
    ocena       INTEGER NOT NULL,
    komentarz   TEXT,
    czas        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS api_keys (
    id             VARCHAR(36) PRIMARY KEY,
    key_id         VARCHAR(12) UNIQUE NOT NULL,
    key_hash       TEXT NOT NULL,
    name           TEXT UNIQUE,
    created_by     TEXT,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at     TIMESTAMP,
    scopes         TEXT,
    quota          TEXT,
    rate_limit     TEXT,
    revoked        BOOLEAN DEFAULT FALSE,
    meta           TEXT,
    last_used_at   TIMESTAMP,
    usage_count    INTEGER DEFAULT 0
);
