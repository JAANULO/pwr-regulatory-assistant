from flask import Blueprint, request, jsonify
from core.settings import ADMIN_TOKEN
from core.bd import polacz, TRYB
from .repository import ApiKeysRepository
from .service import ApiKeyService
from .middleware import init_api_key_middleware
from typing import Any, Dict

__all__ = [
    "api_keys_bp",
    "init_api_key_middleware",
    "api_key_service",
]

# Inicjalizacja instancji
api_keys_repo = ApiKeysRepository(polacz, TRYB)
api_key_service = ApiKeyService(api_keys_repo)

api_keys_bp = Blueprint("api_keys", __name__, url_prefix="/admin/api-keys")


@api_keys_bp.before_request
def require_admin_token() -> Any:
    # Zabezpieczenie endpointów administracyjnych
    token = request.args.get("token") or (request.get_json(silent=True) or {}).get(
        "token"
    )
    if token != ADMIN_TOKEN:
        return jsonify({"error": "Unauthorized"}), 403


@api_keys_bp.route("", methods=["POST"])
def create_key() -> Any:
    from typing import Any, Dict, List, Optional

    dane: Dict[str, Any] = request.get_json(force=True) if request.is_json else {}
    name: str = dane.get("name", "").strip()
    if not name:
        return jsonify({"error": "Pole 'name' jest wymagane"}), 400

    scopes: List[str] = dane.get("scopes", ["all"])
    quota: Dict[str, Any] = dane.get("quota", {})
    rate_limit: Dict[str, Any] = dane.get("rate_limit", {"per_min": 60})
    created_by: str = str(dane.get("created_by", "admin"))

    exp = dane.get("expires_at")
    expires_at: Optional[str] = None
    if exp:
        from datetime import datetime

        try:
            datetime.fromisoformat(str(exp))
            expires_at = str(exp)
        except ValueError:
            return jsonify(
                {
                    "error": f"Niepoprawny format daty 'expires_at': '{exp}'. Oczekiwany format ISO 8601 (np. YYYY-MM-DD lub YYYY-MM-DDTHH:MM:SS)."
                }
            ), 400
    meta: Dict[str, Any] = dane.get("meta", {})

    try:
        key_id, raw_key = api_key_service.create_api_key(
            created_by=created_by,
            name=name,
            scopes=scopes,
            quota=quota,
            rate_limit=rate_limit,
            expires_at=expires_at,
            meta=meta,
        )
    except Exception as e:
        return jsonify(
            {
                "error": f"Błąd tworzenia klucza. Upewnij się, że nazwa '{name}' jest unikalna. Szegóły błędu: {e}"
            }
        ), 409

    return jsonify(
        {
            "key_id": key_id,
            "api_key": raw_key,
            "meta": meta,
            "message": "Store the api_key safely. It won't be shown again.",
        }
    ), 201


@api_keys_bp.route("", methods=["GET"])
def list_keys() -> Any:
    keys = api_keys_repo.list_all()
    return jsonify(keys), 200


@api_keys_bp.route("/<key_id>/revoke", methods=["POST"])
def revoke_key(key_id: str) -> Any:
    api_keys_repo.revoke(key_id)
    return jsonify({"status": "revoked", "key_id": key_id}), 200


@api_keys_bp.route("/<key_id>/rotate", methods=["POST"])
def rotate_key(key_id: str) -> Any:
    # Prosta rotacja: uniewaznij stary, utworz nowy o tych samych parametrach
    record = api_keys_repo.get_by_key_id(key_id)
    if not record:
        return jsonify({"error": "Key not found"}), 404

    api_keys_repo.revoke(key_id)

    import json

    from typing import Dict, Any, List, Optional

    scopes_val: List[str] = (
        json.loads(record.get("scopes", "[]")) if record.get("scopes") else ["all"]
    )
    quota_val: Dict[str, Any] = (
        json.loads(record.get("quota", "{}")) if record.get("quota") else {}
    )
    rl_val: Dict[str, Any] = (
        json.loads(record.get("rate_limit", "{}")) if record.get("rate_limit") else {}
    )
    exp_val = record.get("expires_at")
    exp_val_typed: Optional[str] = str(exp_val) if exp_val else None
    meta_val: Dict[str, Any] = (
        json.loads(record.get("meta", "{}")) if record.get("meta") else {}
    )
    name_val: str = str(record.get("name") or "Rotowany klucz")

    try:
        new_key_id, new_raw_key = api_key_service.create_api_key(
            created_by=str(record.get("created_by") or "admin"),
            name=name_val,
            scopes=scopes_val,
            quota=quota_val,
            rate_limit=rl_val,
            expires_at=exp_val_typed,
            meta=meta_val,
        )
    except Exception as e:
        return jsonify(
            {
                "error": f"Błąd rotacji. Upewnij się, że zwalniana nazwa nie ma konfliktów: {e}"
            }
        ), 409

    return jsonify(
        {
            "old_key_id": key_id,
            "new_key_id": new_key_id,
            "api_key": new_raw_key,
            "message": "Key rotated successfully.",
        }
    ), 200


@api_keys_bp.route("/<key_id>/name", methods=["PUT"])
def change_key_name(key_id: str) -> Any:
    dane: Dict[str, Any] = request.get_json(force=True) if request.is_json else {}
    new_name: str = dane.get("name", "").strip()

    if not new_name:
        return jsonify({"error": "Pole 'name' jest wymagane"}), 400

    try:
        api_keys_repo.rename_key(key_id, new_name)
        return jsonify(
            {"status": "renamed", "key_id": key_id, "new_name": new_name}
        ), 200
    except Exception as e:
        return jsonify(
            {
                "error": f"Nie udało się zmienić nazwy. Nowa nazwa '{new_name}' może już istnieć. ({str(e)})"
            }
        ), 409
