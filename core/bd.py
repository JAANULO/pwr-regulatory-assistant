"""
bd.py – warstwa połączeń z bazą danych (SQLite lokalnie / PostgreSQL produkcja).
TRYB wykrywany automatycznie przez zmienną środowiskową DATABASE_URL.

Publiczne API tej klasy (funkcje) jest zachowane bez zmian — delegują one
do klas repozytoriów w `domain/repositories/`, które enkapsulują SQL.
"""

import logging
import os
import sqlite3
from contextlib import contextmanager

from .settings import DATABASE_URL, DB_BACKEND, DB_CONNECT_TIMEOUT, DB_SSLMODE

TRYB = DB_BACKEND

_LOG = logging.getLogger("asystent.db")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PLIK_DB = os.path.join(BASE_DIR, "..", "data", "database", "asystent.db")


if TRYB == "postgres":
    try:
        from psycopg2.extras import RealDictCursor  # type: ignore
        from psycopg2.pool import ThreadedConnectionPool  # type: ignore

        pg_pool = ThreadedConnectionPool(
            1,
            10,
            DATABASE_URL,
            connect_timeout=DB_CONNECT_TIMEOUT,
            sslmode=DB_SSLMODE,
        )
    except Exception as e:
        _LOG.warning("PostgreSQL niedostepny, fallback do SQLite: %s", e)
        TRYB = "sqlite"
        pg_pool = None
else:
    pg_pool = None


@contextmanager
def polacz():
    if TRYB == "postgres":
        conn = pg_pool.getconn()
        conn.cursor_factory = RealDictCursor
        try:
            yield conn
        finally:
            pg_pool.putconn(conn)
    else:
        conn = sqlite3.connect(PLIK_DB)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()


def inicjalizuj():
    """Tworzy tabele jeśli nie istnieją (SQLite i PostgreSQL)."""
    if TRYB == "postgres":
        with polacz() as conn:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS pytania (
                    id          SERIAL PRIMARY KEY,
                    pytanie     TEXT NOT NULL,
                    tytul       TEXT,
                    podobienstwo REAL,
                    odpowiedz   TEXT,
                    baza        TEXT DEFAULT 'studia',
                    czas        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id          SERIAL PRIMARY KEY,
                    pytanie_id  INTEGER REFERENCES pytania(id),
                    ocena       INTEGER NOT NULL,
                    komentarz   TEXT,
                    czas        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    id             VARCHAR(36) PRIMARY KEY,
                    key_id         VARCHAR(12) UNIQUE NOT NULL,
                    key_hash       TEXT NOT NULL,
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
            """)
            conn.commit()
            _LOG.info("Baza PostgreSQL zainicjalizowana pomyślnie")
    else:
        with polacz() as conn:
            conn.executescript("""
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
            """)

            # Automatyczna migracja: dodaj kolumnę 'odpowiedz' jeśli tabela istniała bez niej
            try:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(pytania)")
                columns = [row[1] for row in cursor.fetchall()]
                if "odpowiedz" not in columns:
                    conn.execute("ALTER TABLE pytania ADD COLUMN odpowiedz TEXT")
                    _LOG.info(
                        "Migracja: Dodano kolumnę 'odpowiedz' do tabeli 'pytania'"
                    )
            except Exception as e:
                _LOG.warning("Błąd migracji kolumny 'odpowiedz': %s", e)


# ── Repozytoria (inicjalizowane raz przy imporcie modułu) ─────────────────────

from domain.repositories.pytania_repo import PytaniaRepository  # type: ignore
from domain.repositories.feedback_repo import FeedbackRepository  # type: ignore

_pytania = PytaniaRepository(polacz, TRYB)
_feedback = FeedbackRepository(polacz, TRYB)


# ── Publiczne API — thin wrappers delegujące do repozytoriów ──────────────────


def zapisz_pytanie(
    pytanie: str,
    tytul: str | None,
    podobienstwo: float,
    baza: str = "studia",
    odpowiedz: str | None = None,
) -> int | None:
    return _pytania.zapisz(pytanie, tytul, podobienstwo, baza, odpowiedz)


def pobierz_pytanie(pytanie_id: int) -> dict | None:
    return _pytania.pobierz(pytanie_id)


def pobierz_ostatnie_pytania(limit: int = 10) -> list[dict]:
    return _pytania.pobierz_ostatnie(limit)


def pobierz_statystyki() -> dict:
    return _pytania.pobierz_statystyki()


def zapisz_feedback(pytanie_id: int, ocena: int, komentarz: str | None = None) -> bool:
    return _feedback.zapisz(pytanie_id, ocena, komentarz)


def pobierz_wspolczynniki_zbiorczo() -> dict[str, float]:
    return _feedback.pobierz_wspolczynniki_zbiorczo()
