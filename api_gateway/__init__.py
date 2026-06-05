from flask import Blueprint, request, jsonify
from core.settings import ADMIN_TOKEN
from core.bd import polacz, TRYB
from .repository import ApiKeysRepository
from .service import ApiKeyService
from .middleware import init_api_key_middleware

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
def require_admin_token():
    # Zabezpieczenie endpointów administracyjnych
    token = request.args.get("token") or (request.get_json(silent=True) or {}).get(
        "token"
    )
    if token != ADMIN_TOKEN:
        return jsonify({"error": "Unauthorized"}), 403


@api_keys_bp.route("", methods=["POST"])
def create_key():
    dane = request.get_json(force=True) if request.is_json else {}
    scopes = dane.get("scopes", ["all"])
    quota = dane.get("quota", {})
    rate_limit = dane.get("rate_limit", {"per_min": 60})
    created_by = dane.get("created_by", "admin")
    expires_at = dane.get("expires_at")
    meta = dane.get("meta", {})

    key_id, raw_key = api_key_service.create_api_key(
        created_by=created_by,
        scopes=scopes,
        quota=quota,
        rate_limit=rate_limit,
        expires_at=expires_at,
        meta=meta,
    )

    return jsonify(
        {
            "key_id": key_id,
            "api_key": raw_key,
            "meta": meta,
            "message": "Store the api_key safely. It won't be shown again.",
        }
    ), 201


@api_keys_bp.route("", methods=["GET"])
def list_keys():
    keys = api_keys_repo.list_all()
    return jsonify(keys), 200


@api_keys_bp.route("/<key_id>/revoke", methods=["POST"])
def revoke_key(key_id):
    api_keys_repo.revoke(key_id)
    return jsonify({"status": "revoked", "key_id": key_id}), 200


@api_keys_bp.route("/<key_id>/rotate", methods=["POST"])
def rotate_key(key_id):
    # Prosta rotacja: uniewaznij stary, utworz nowy o tych samych parametrach
    record = api_keys_repo.get_by_key_id(key_id)
    if not record:
        return jsonify({"error": "Key not found"}), 404

    api_keys_repo.revoke(key_id)

    import json

    new_key_id, new_raw_key = api_key_service.create_api_key(
        created_by=record.get("created_by"),
        scopes=json.loads(record.get("scopes", "[]"))
        if record.get("scopes")
        else ["all"],
        quota=json.loads(record.get("quota", "{}")) if record.get("quota") else {},
        rate_limit=json.loads(record.get("rate_limit", "{}"))
        if record.get("rate_limit")
        else {},
        expires_at=record.get("expires_at"),
        meta=json.loads(record.get("meta", "{}")) if record.get("meta") else {},
    )

    return jsonify(
        {
            "old_key_id": key_id,
            "new_key_id": new_key_id,
            "api_key": new_raw_key,
            "message": "Key rotated successfully.",
        }
    ), 200
