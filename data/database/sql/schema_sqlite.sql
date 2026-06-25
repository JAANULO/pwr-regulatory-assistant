CREATE TABLE IF NOT EXISTS pytania (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    pytanie     TEXT NOT NULL,
    tytul       TEXT,
    podobienstwo REAL,
    odpowiedz   TEXT,
    baza        TEXT DEFAULT 'studia',
    czas        TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS feedback (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    pytanie_id  INTEGER REFERENCES pytania(id),
    ocena       INTEGER NOT NULL,
    komentarz   TEXT,
    czas        TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS api_keys (
    id             TEXT PRIMARY KEY,
    key_id         TEXT UNIQUE NOT NULL,
    key_hash       TEXT NOT NULL,
    name           TEXT UNIQUE,
    created_by     TEXT,
    created_at     TEXT DEFAULT (datetime('now','localtime')),
    expires_at     TEXT,
    scopes         TEXT,
    quota          TEXT,
    rate_limit     TEXT,
    revoked        INTEGER DEFAULT 0,
    meta           TEXT,
    last_used_at   TEXT,
    usage_count    INTEGER DEFAULT 0
);
