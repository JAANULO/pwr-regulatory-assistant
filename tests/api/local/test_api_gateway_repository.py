import pytest
from api_gateway.repository import ApiKeysRepository
import sqlite3


@pytest.fixture
def repo():
    # Używamy jednego współdzielonego połączenia do bazy SQLite w pamięci dla testów izolowanych
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    def connect_fn():
        return conn

    # Przygotowanie schematu bazy danych
    with connect_fn() as conn:
        conn.execute("""
            CREATE TABLE api_keys (
                id TEXT PRIMARY KEY,
                key_id TEXT UNIQUE NOT NULL,
                key_hash TEXT NOT NULL,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                scopes JSON,
                quota JSON,
                rate_limit JSON,
                revoked INTEGER DEFAULT 0,
                meta JSON,
                last_used_at TIMESTAMP,
                usage_count INTEGER DEFAULT 0
            )
        """)
        conn.commit()

    return ApiKeysRepository(connect_fn, tryb="sqlite")


def test_create_and_get_key(repo):
    key_id = "test_key_id"
    key_hash = "fake_hash_123"
    created_by = "admin"

    # Utworzenie
    repo.create(
        key_id=key_id,
        key_hash=key_hash,
        created_by=created_by,
        scopes=["all"],
        quota={"max": 100},
        rate_limit={"per_min": 10},
    )

    # Odczyt
    record = repo.get_by_key_id(key_id)
    assert record is not None
    assert record["key_id"] == key_id
    assert record["key_hash"] == key_hash
    assert record["created_by"] == created_by
    assert record["revoked"] == 0
    assert record["usage_count"] == 0


def test_revoke_key(repo):
    key_id = "test_revoke"
    repo.create(
        key_id=key_id, key_hash="h", created_by="a", scopes=[], quota={}, rate_limit={}
    )

    repo.revoke(key_id)
    record = repo.get_by_key_id(key_id)
    assert record["revoked"] == 1


def test_update_usage(repo):
    key_id = "test_usage"
    repo.create(
        key_id=key_id, key_hash="h", created_by="a", scopes=[], quota={}, rate_limit={}
    )

    repo.update_usage(key_id)
    repo.update_usage(key_id)

    record = repo.get_by_key_id(key_id)
    assert record["usage_count"] == 2
