import os
import sys
import platform
import traceback
import sqlite3
from datetime import datetime


def execute_debug_info(data_dir, db_path, admin_token, request_token):
    """
    Zwraca szczegółowe informacje o stanie systemu i środowiska.
    Działa tylko jeśli request_token == admin_token.
    """
    if not request_token or request_token != admin_token:
        return {"error": "Brak uprawnień do diagnostyki"}, 403

    info = {
        "timestamp": datetime.now().isoformat(),
        "system": {
            "os": platform.system(),
            "os_release": platform.release(),
            "python_version": sys.version,
            "cwd": os.getcwd(),
        },
        "directories": {
            "data_dir": {
                "path": data_dir,
                "exists": os.path.exists(data_dir),
                "is_dir": os.path.isdir(data_dir)
                if os.path.exists(data_dir)
                else False,
                "contents": (
                    os.listdir(data_dir)
                    if os.path.exists(data_dir) and os.path.isdir(data_dir)
                    else []
                ),
            }
        },
        "database": {
            "path": db_path,
            "exists": os.path.exists(db_path),
            "writable": (
                os.access(db_path, os.W_OK) if os.path.exists(db_path) else False
            ),
        },
        "env_vars": {
            "APP_ENV": os.getenv("APP_ENV"),
            "PORT": os.getenv("PORT"),
            "DATABASE_URL_SET": os.getenv("DATABASE_URL") is not None,
            "LOG_LEVEL": os.getenv("LOG_LEVEL"),
        },
    }

    # Próba połączenia z bazą
    try:
        conn = sqlite3.connect(db_path, timeout=1)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        info["database"]["tables"] = [row[0] for row in cursor.fetchall()]
        conn.close()
    except Exception as e:
        info["database"]["error"] = str(e)

    return info, 200


def get_error_details(exception):
    """Pomocnik do wyciągania tracebacku."""
    return traceback.format_exc()
