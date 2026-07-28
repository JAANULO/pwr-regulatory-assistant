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
KATALOG_SQL = os.path.join(BASE_DIR, "..", "data", "database", "sql")

WYMAGANE_KLUCZE = {
    "zapisz_feedback",
    "pobierz_wspolczynniki_zbiorczo",
    "zapisz_pytanie",
    "pobierz_pytanie",
    "pobierz_ostatnie",
    "pobierz_statystyki_total",
    "pobierz_statystyki_avg",
    "pobierz_statystyki_top",
    "pobierz_statystyki_zle",
    "pobierz_statystyki_dzienne",
    "pobierz_statystyki_ostatnie",
}


def wczytaj_zapytania(sciezka_pliku: str) -> dict[str, str]:
    zapytania = {}
    if not os.path.exists(sciezka_pliku):
        raise FileNotFoundError(f"Nie znaleziono pliku SQL: {sciezka_pliku}")

    current_name = None
    lines_accumulator: list[str] = []

    with open(sciezka_pliku, "r", encoding="utf-8") as f:
        for line in f:
            line_stripped = line.strip()
            if line_stripped.startswith("-- name:"):
                if current_name:
                    zapytania[current_name] = "\n".join(lines_accumulator).strip()
                current_name = line_stripped[len("-- name:") :].strip()
                lines_accumulator = []
            elif current_name is not None:
                lines_accumulator.append(line)

        if current_name:
            zapytania[current_name] = "\n".join(lines_accumulator).strip()

    brakujace = WYMAGANE_KLUCZE - set(zapytania.keys())
    if brakujace:
        raise ValueError(
            f"Blad wczytywania zapytan z {sciezka_pliku}. Brakujace wymagane zapytania: {', '.join(brakujace)}"
        )
    return zapytania


PLIK_ZAPYTAN = os.path.join(
    KATALOG_SQL, "queries_postgres.sql" if TRYB == "postgres" else "queries_sqlite.sql"
)
ZAPYTANIA = wczytaj_zapytania(PLIK_ZAPYTAN)


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
    if TRYB == "postgres" and pg_pool is not None:
        conn = pg_pool.getconn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
        except Exception:
            # Połączenie martwe (Software caused connection abort), pobierz nowe
            try:
                pg_pool.putconn(conn, close=True)
            except Exception as e:
                _LOG.warning(f"Błąd przy zamykaniu martwego połączenia: {e}")
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
            sciezka_schematu = os.path.join(KATALOG_SQL, "schema_postgres.sql")
            with open(sciezka_schematu, "r", encoding="utf-8") as f:
                schemat = f.read()
            cur.execute(schemat)

            # Automatyczna migracja PostgreSQL dla name
            try:
                cur.execute("ALTER TABLE api_keys ADD COLUMN name TEXT UNIQUE;")
                _LOG.info(
                    "Migracja: Dodano kolumnę 'name' do tabeli 'api_keys' (PostgreSQL)"
                )
            except Exception as e:
                conn.rollback()
                pgcode = getattr(e, "pgcode", None)
                if pgcode == "42701":
                    _LOG.debug(
                        "Migracja PostgreSQL: kolumna 'name' już istnieje (kod 42701)"
                    )
                else:
                    _LOG.warning(
                        "Błąd automatycznej migracji PostgreSQL (dodawanie kolumny 'name'): %s",
                        e,
                        exc_info=True,
                    )
            else:
                conn.commit()

            conn.commit()
            _LOG.info("Baza PostgreSQL zainicjalizowana pomyślnie")
    else:
        with polacz() as conn:
            sciezka_schematu = os.path.join(KATALOG_SQL, "schema_sqlite.sql")
            with open(sciezka_schematu, "r", encoding="utf-8") as f:
                schemat = f.read()
            conn.executescript(schemat)

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
                _LOG.warning("Błąd migracji kolumny 'odpowiedz': %s", e, exc_info=True)

            # Automatyczna migracja dla api_keys: dodaj 'name'
            try:
                cursor.execute("PRAGMA table_info(api_keys)")
                columns_api = [row[1] for row in cursor.fetchall()]
                if "name" not in columns_api:
                    conn.execute("ALTER TABLE api_keys RENAME TO api_keys_old")
                    conn.execute("""
                        CREATE TABLE api_keys (
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
                    """)
                    conn.execute("""
                        INSERT INTO api_keys (id, key_id, key_hash, created_by, created_at, expires_at, scopes, quota, rate_limit, revoked, meta, last_used_at, usage_count, name)
                        SELECT id, key_id, key_hash, created_by, created_at, expires_at, scopes, quota, rate_limit, revoked, meta, last_used_at, usage_count, 'Stary klucz ' || key_id
                        FROM api_keys_old;
                    """)
                    conn.execute("DROP TABLE api_keys_old")
                    _LOG.info(
                        "Migracja: Przebudowano tabelę 'api_keys' i dodano 'name' (SQLite)"
                    )
            except Exception as e:
                _LOG.warning(
                    "Błąd migracji kolumny 'name' w api_keys: %s", e, exc_info=True
                )


# ── Repozytoria (inicjalizowane raz przy imporcie modułu) ─────────────────────

from domain.repositories.pytania_repo import PytaniaRepository  # type: ignore
from domain.repositories.feedback_repo import FeedbackRepository  # type: ignore

_pytania = PytaniaRepository(polacz, TRYB, ZAPYTANIA)
_feedback = FeedbackRepository(polacz, TRYB, ZAPYTANIA)


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
