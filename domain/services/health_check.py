import os
import json
import time
import logging
from typing import Tuple, Dict, Any

logger = logging.getLogger("asystent.health")


def execute_health_check(
    data_dir: str,
    plik_bazy_json: str,
    admin_token: str,
    provided_token: str,
    container: Any,
    cache: Dict[str, Any],
) -> Tuple[Dict[str, Any], int]:
    """
    Weryfikuje integralność infrastruktury i status komponentów (Punkt 3.2 Architektury).
    """
    if provided_token != admin_token:
        return {"error": "Brak dostępu (Nieprawidłowy token)"}, 403

    start_time = time.time()

    status: Dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "OK",
        "checks": {},
    }

    # 1. Sprawdzenie Bazy Wiedzy (JSON)
    try:
        if not os.path.exists(plik_bazy_json):
            status["checks"]["knowledge_base"] = "ERROR: File missing"
            status["status"] = "DEGRADED"
        else:
            with open(plik_bazy_json, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    count = len(data)
                elif isinstance(data, dict):
                    count = len(data.get("paragrafy", []))
                else:
                    count = 0
                status["checks"]["knowledge_base"] = f"OK ({count} paragraphs)"
    except Exception as e:
        status["checks"]["knowledge_base"] = f"ERROR: {str(e)}"
        status["status"] = "DEGRADED"

    # 2. Sprawdzenie Połączenia SQL
    try:
        from core.bd import polacz

        with polacz() as conn:
            cursor = conn.cursor()
            # Proste zapytanie sprawdzające istnienie tabel
            if os.environ.get("DATABASE_URL"):
                cursor.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
                )
                tables = [
                    row[0] if isinstance(row, tuple) else row["table_name"]
                    for row in cursor.fetchall()
                ]
            else:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                # Obsługa sqlite3.Row i zwykłych krotek
                rows = cursor.fetchall()
                tables = []
                for r in rows:
                    if isinstance(r, (tuple, list)):
                        tables.append(r[0])
                    elif hasattr(r, "keys"):  # sqlite3.Row
                        tables.append(r["name"])
                    else:
                        tables.append(str(r))

            if "pytania" in tables:
                status["checks"]["sql_database"] = (
                    "OK (connected, table 'pytania' exists)"
                )
            else:
                status["checks"]["sql_database"] = (
                    f"ERROR: Table 'pytania' missing (found: {tables})"
                )
                status["status"] = "ERROR"
    except Exception as e:
        status["checks"]["sql_database"] = f"ERROR: {str(e)}"
        status["status"] = "ERROR"

    # 3. Status Wyszukiwarki (DI Container)
    if container.wyszukiwarka:
        status["checks"]["search_engine"] = "OK (initialized)"
    else:
        status["checks"]["search_engine"] = "ERROR: Not initialized"
        status["status"] = "DEGRADED"

    # 4. Status Cache'owania
    cache_size = len(cache)
    status["checks"]["memory_cache"] = f"OK ({cache_size} entries)"

    # 5. Środowisko
    status["checks"]["environment"] = (
        "Production (PostgreSQL)"
        if os.environ.get("DATABASE_URL")
        else "Development (SQLite)"
    )

    # Ustalenie finalnego statusu HTTP
    if status["status"] == "OK":
        http_status = 200
    elif status["status"] == "DEGRADED":
        http_status = 503
    else:
        http_status = 500

    status["latency_ms"] = int((time.time() - start_time) * 1000)

    return status, http_status
