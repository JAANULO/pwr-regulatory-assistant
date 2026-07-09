import hashlib
import secrets
import string
import time
from typing import Tuple, Dict, Any, Optional
import json
import logging
from core.settings import REDIS_URL

_LOG = logging.getLogger("asystent.api_gateway")

_redis_client = None
if REDIS_URL:
    try:
        import redis  # type: ignore

        _redis_client = redis.from_url(REDIS_URL)  # type: ignore
        _LOG.info("Redis Rate Limiter zainicjowany pomyślnie.")
    except Exception as e:
        _LOG.error(f"Nie udalo sie zinicjowac Redis: {e}")

# Fallback: in-memory Rate Limiter
_RATE_LIMITS: Dict[str, Any] = {}


class ApiKeyService:
    def __init__(self, repository):
        self.repo = repository

    def _generate_raw_secret(self, length=32) -> str:
        chars = string.ascii_letters + string.digits
        return "".join(secrets.choice(chars) for _ in range(length))

    def _hash_secret(self, secret: str) -> str:
        return hashlib.sha256(secret.encode("utf-8")).hexdigest()

    def create_api_key(
        self,
        created_by: str,
        name: str,
        scopes: list,
        quota: dict,
        rate_limit: dict,
        expires_at: Optional[str] = None,
        meta: Optional[dict] = None,
    ) -> Tuple[str, str]:
        """Tworzy nowy klucz API i zwraca (key_id, raw_api_key). Zapisuje tylko hash."""
        key_id = self._generate_raw_secret(10)
        raw_secret = self._generate_raw_secret(32)
        full_raw_key = f"{key_id}.{raw_secret}"

        key_hash = self._hash_secret(full_raw_key)

        self.repo.create(
            key_id=key_id,
            key_hash=key_hash,
            name=name,
            created_by=created_by,
            scopes=scopes,
            quota=quota,
            rate_limit=rate_limit,
            expires_at=expires_at,
            meta=meta,
        )
        return key_id, full_raw_key

    def validate_key(
        self, full_raw_key: str, endpoint_scope: str
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Sprawdza autentyczność, quota oraz rate limit klucza."""
        if not full_raw_key or "." not in full_raw_key:
            return False, "Invalid key format", {}

        key_id, _ = full_raw_key.split(".", 1)
        record = self.repo.get_by_key_id(key_id)

        if not record:
            return False, "Key not found", {}

        # 1. Sprawdz hash
        expected_hash = self._hash_secret(full_raw_key)
        if not secrets.compare_digest(expected_hash, record["key_hash"]):
            return False, "Invalid key", {}

        # 2. Sprawdz revokacje
        if record["revoked"]:
            return False, "Key revoked", {}

        # 3. Sprawdz date waznosci
        expires_at_val = record.get("expires_at")
        if expires_at_val:
            from datetime import datetime

            try:
                if isinstance(expires_at_val, datetime):
                    expires_dt = expires_at_val
                else:
                    expires_dt = datetime.fromisoformat(str(expires_at_val))
                if expires_dt.tzinfo is not None:
                    expires_dt = expires_dt.astimezone().replace(tzinfo=None)
                if datetime.now() > expires_dt:
                    return False, "Key expired", {}
            except Exception as e:
                _LOG.warning(f"Blad walidacji daty wygasniecia klucza {key_id}: {e}")

        # 4. Sprawdz scope
        if record["scopes"]:
            try:
                scopes = json.loads(record["scopes"])
                if endpoint_scope not in scopes and "all" not in scopes:
                    return False, "Scope not allowed", {}
            except Exception as e:
                _LOG.warning(f"Blad parsowania scopes: {e}")

        # 5. Rate Limit
        rl = {}
        if record["rate_limit"]:
            try:
                rl = json.loads(record["rate_limit"])
            except Exception as e:
                _LOG.warning(f"Blad parsowania rate_limit: {e}")

        if "per_min" in rl:
            limit = int(rl["per_min"])
            now = time.time()
            window_start = now - (now % 60)

            limit_exceeded = False

            if _redis_client:
                r_key = f"rl:{key_id}:{int(window_start)}"
                try:
                    count = _redis_client.incr(r_key)
                    if count == 1:
                        _redis_client.expire(r_key, 60)
                    if count > limit:
                        limit_exceeded = True
                except Exception as e:
                    _LOG.error(f"Błąd redisa: {e}")
                    limit_exceeded = self._in_memory_rate_limit(
                        key_id, limit, window_start
                    )
            else:
                limit_exceeded = self._in_memory_rate_limit(key_id, limit, window_start)

            if limit_exceeded:
                return False, "Rate limit exceeded", {"status_code": 429}

        self.repo.update_usage(key_id)

        return True, "OK", record

    def _in_memory_rate_limit(
        self, key_id: str, limit: int, window_start: float
    ) -> bool:
        """Prywatna funkcja fallback obsługująca stary słownik (RAM)."""
        user_limits = _RATE_LIMITS.setdefault(
            key_id, {"window_start": window_start, "count": 0}
        )
        if user_limits["window_start"] != window_start:
            user_limits["window_start"] = window_start
            user_limits["count"] = 0

        if user_limits["count"] >= limit:
            return True

        user_limits["count"] += 1
        return False
