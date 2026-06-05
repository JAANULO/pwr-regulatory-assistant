import json
import uuid
from typing import Optional


class ApiKeysRepository:
    def __init__(self, polacz_fn, tryb: str):
        self.polacz = polacz_fn
        self.tryb = tryb

    def create(
        self,
        key_id: str,
        key_hash: str,
        created_by: str,
        scopes: list,
        quota: dict,
        rate_limit: dict,
        expires_at=None,
        meta: Optional[dict] = None,
    ) -> str:
        new_id = str(uuid.uuid4())
        scopes_str = json.dumps(scopes) if scopes else "[]"
        quota_str = json.dumps(quota) if quota else "{}"
        rate_limit_str = json.dumps(rate_limit) if rate_limit else "{}"
        meta_str = json.dumps(meta) if meta else "{}"

        with self.polacz() as conn:
            cur = conn.cursor()
            if self.tryb == "postgres":
                cur.execute(
                    """
                    INSERT INTO api_keys 
                    (id, key_id, key_hash, created_by, scopes, quota, rate_limit, expires_at, meta)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                    (
                        new_id,
                        key_id,
                        key_hash,
                        created_by,
                        scopes_str,
                        quota_str,
                        rate_limit_str,
                        expires_at,
                        meta_str,
                    ),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO api_keys 
                    (id, key_id, key_hash, created_by, scopes, quota, rate_limit, expires_at, meta)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        new_id,
                        key_id,
                        key_hash,
                        created_by,
                        scopes_str,
                        quota_str,
                        rate_limit_str,
                        expires_at,
                        meta_str,
                    ),
                )
            conn.commit()
            return new_id

    def get_by_key_id(self, key_id: str) -> Optional[dict]:
        with self.polacz() as conn:
            cur = conn.cursor()
            if self.tryb == "postgres":
                cur.execute("SELECT * FROM api_keys WHERE key_id = %s", (key_id,))
            else:
                cur.execute("SELECT * FROM api_keys WHERE key_id = ?", (key_id,))
            row = cur.fetchone()
            if not row:
                return None
            return dict(row)

    def list_all(self):
        with self.polacz() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, key_id, created_by, created_at, expires_at, scopes, quota, rate_limit, revoked, meta, last_used_at, usage_count FROM api_keys ORDER BY created_at DESC"
            )
            rows = cur.fetchall()
            return [dict(r) for r in rows]

    def revoke(self, key_id: str):
        with self.polacz() as conn:
            cur = conn.cursor()
            if self.tryb == "postgres":
                cur.execute(
                    "UPDATE api_keys SET revoked = TRUE WHERE key_id = %s", (key_id,)
                )
            else:
                cur.execute(
                    "UPDATE api_keys SET revoked = 1 WHERE key_id = ?", (key_id,)
                )
            conn.commit()

    def update_usage(self, key_id: str):
        with self.polacz() as conn:
            cur = conn.cursor()
            if self.tryb == "postgres":
                cur.execute(
                    "UPDATE api_keys SET usage_count = usage_count + 1, last_used_at = CURRENT_TIMESTAMP WHERE key_id = %s",
                    (key_id,),
                )
            else:
                cur.execute(
                    "UPDATE api_keys SET usage_count = usage_count + 1, last_used_at = datetime('now','localtime') WHERE key_id = ?",
                    (key_id,),
                )
            conn.commit()
