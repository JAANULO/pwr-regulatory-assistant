import pytest
import json
from api_gateway.service import ApiKeyService


class MockRepo:
    def __init__(self):
        self.records = {}
        self.usage = {}

    def create(
        self,
        key_id,
        key_hash,
        created_by,
        scopes,
        quota,
        rate_limit,
        expires_at=None,
        meta=None,
    ):
        self.records[key_id] = {
            "key_id": key_id,
            "key_hash": key_hash,
            "created_by": created_by,
            "scopes": json.dumps(scopes) if scopes else "[]",
            "quota": json.dumps(quota) if quota else "{}",
            "rate_limit": json.dumps(rate_limit) if rate_limit else "{}",
            "revoked": 0,
            "meta": json.dumps(meta) if meta else "{}",
        }
        self.usage[key_id] = 0

    def get_by_key_id(self, key_id):
        return self.records.get(key_id)

    def update_usage(self, key_id):
        if key_id in self.usage:
            self.usage[key_id] += 1


@pytest.fixture
def service():
    return ApiKeyService(MockRepo())


def test_create_and_validate_key(service):
    key_id, raw_key = service.create_api_key(
        created_by="admin", scopes=["ask"], quota={}, rate_limit={"per_min": 5}
    )

    assert key_id in raw_key
    assert "." in raw_key

    # Validacja poprawnego klucza
    is_valid, msg, meta = service.validate_key(raw_key, "ask")
    assert is_valid is True
    assert msg == "OK"
    assert meta["key_id"] == key_id


def test_validate_key_invalid_hash(service):
    key_id, raw_key = service.create_api_key(
        created_by="admin", scopes=["ask"], quota={}, rate_limit={}
    )
    invalid_key = f"{key_id}.badsecret123"

    is_valid, msg, meta = service.validate_key(invalid_key, "ask")
    assert is_valid is False
    assert msg == "Invalid key"


def test_validate_key_scope(service):
    _, raw_key = service.create_api_key(
        created_by="admin", scopes=["other"], quota={}, rate_limit={}
    )

    is_valid, msg, _ = service.validate_key(raw_key, "ask")
    assert is_valid is False
    assert msg == "Scope not allowed"


def test_rate_limit(service):
    key_id, raw_key = service.create_api_key(
        created_by="a", scopes=["all"], quota={}, rate_limit={"per_min": 2}
    )

    # 1 użycie
    is_valid, _, _ = service.validate_key(raw_key, "ask")
    assert is_valid is True

    # 2 użycie
    is_valid, _, _ = service.validate_key(raw_key, "ask")
    assert is_valid is True

    # 3 użycie (przekroczenie)
    is_valid, msg, meta = service.validate_key(raw_key, "ask")
    assert is_valid is False
    assert msg == "Rate limit exceeded"
    assert meta["status_code"] == 429
