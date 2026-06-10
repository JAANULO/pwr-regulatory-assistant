from flask import request, jsonify, g


def init_api_key_middleware(app, api_key_service, protected_routes=None):
    if protected_routes is None:
        protected_routes = ["/zapytaj"]

    @app.before_request
    def check_api_key():
        if request.path not in protected_routes:
            return None

        if request.method == "OPTIONS":
            return None

        # Przepusc jesli podano wlasciwy admin_token, jako wyjatek.
        # W praktyce warto to oddzielic, ale dla wstecznej kompatybilnosci.
        # Sprawdzane sa naglowki
        api_key = request.headers.get("X-Api-Key") or request.headers.get(
            "Authorization"
        )
        if not api_key:
            return jsonify({"error": "Missing API Key"}), 401

        if api_key.startswith("ApiKey "):
            api_key = api_key.split("ApiKey ")[1].strip()
        elif api_key.startswith("Bearer "):
            api_key = api_key.split("Bearer ")[1].strip()

        # Uzywamy nazwy endpointu z protected_routes jako scope
        scope = "ask" if request.path == "/api/zapytaj" else "all"
        is_valid, msg, meta = api_key_service.validate_key(api_key, scope)

        if not is_valid:
            status_code = meta.get("status_code", 401)
            return jsonify({"error": msg}), status_code

        # Przypisanie meta do context global (g) zamiast do request,
        # co niweluje krzyczenie Pylance z VSC (request defaultowo nie pozwala dopisywac pol)
        g.api_key_meta = meta
        return None
