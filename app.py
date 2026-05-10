"""
app.py – serwer Flask dla asystenta regulaminowego PWr
Uruchomienie: python app.py
Adres:        http://localhost:5000
"""

import os
import sys
import time
from collections import OrderedDict

# Ustawienie ścieżki dla modułów lokalnych
ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from flask import Flask, jsonify, render_template, request

from core.settings import (
    ADMIN_TOKEN,
    FLASK_DEBUG,
    FLASK_HOST,
    FLASK_PORT,
)
from core.bd import (
    inicjalizuj,
    pobierz_ostatnie_pytania,
    pobierz_statystyki,
    PLIK_DB,
)
from core.slowniki import ROZSZERZENIA, SYNONIMY
from core.wyszukiwarka import Wyszukiwarka
from domain.services.debug_service import execute_debug_info, get_error_details


app = Flask(__name__)


def _znajdz_rozszerzenie(pytanie_lower: str) -> str:
    """Zwraca rozszerzenie dla pierwszej pasującej frazy lub pusty string."""
    for fraza, rozszerzenie in ROZSZERZENIA.items():
        if fraza in pytanie_lower:
            return rozszerzenie
    return ""


def _wykryj_numer_paragrafu(pytanie: str) -> str | None:
    """Wykrywa numer paragrafu używając scentralizowanej logiki."""
    return Wyszukiwarka.wykryj_numer_paragrafu(pytanie)


def _cache_get(pytanie: str) -> dict | None:
    wpis = CACHE_ODPOWIEDZI.get(pytanie)
    if not wpis:
        return None
    if time.time() - wpis["ts"] > CACHE_TTL_SECONDS:
        CACHE_ODPOWIEDZI.pop(pytanie, None)
        return None
    return wpis["data"]


def _cache_set(pytanie: str, odpowiedz: dict) -> None:
    if pytanie in CACHE_ODPOWIEDZI:
        CACHE_ODPOWIEDZI[pytanie] = {"ts": time.time(), "data": odpowiedz}
        return
    while len(CACHE_ODPOWIEDZI) >= CACHE_MAX_SIZE:
        CACHE_ODPOWIEDZI.popitem(last=False)
    CACHE_ODPOWIEDZI[pytanie] = {"ts": time.time(), "data": odpowiedz}


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
PLIK_BAZY = os.path.join(DATA_DIR, "baza_wiedzy.json")
PLIK_LOG = os.path.join(BASE_DIR, "logs", "log.txt")
PROG_PEWNOSCI = 0.15

MAPA_ZNAKOW = str.maketrans("ąćęłńóśźż", "acelnoszz")

CACHE_TTL_SECONDS = 60 * 60
CACHE_MAX_SIZE = 500
CACHE_ODPOWIEDZI: OrderedDict[str, dict] = OrderedDict()

# ── Kontener zależności (DI) ──────────────────────────────────────────────────
from infrastructure.container import Container

container = Container(base_dir=BASE_DIR, data_dir=DATA_DIR, log_file=PLIK_LOG)
logger = container.logger


def zaladuj_wyszukiwarke() -> None:
    container.initialize_components()


# ── trasy ─────────────────────────────────────────────────────────────────────


@app.route("/")
def index():
    return render_template("index.html")


# --- Tryb Laboratorium (Symulacja BM25) ---
@app.route("/lab")
def lab_view():
    return render_template("lab.html")


@app.route("/zapytaj_symulacja", methods=["POST"])
def zapytaj_symulacja():
    if container.wyszukiwarka is None:
        return jsonify({"blad": "Wyszukiwarka nie załadowana"}), 500

    from domain.services.simulate_question import execute_simulate_question

    payload, status = execute_simulate_question(
        request.get_json(force=True), container.wyszukiwarka, logger
    )
    return jsonify(payload), status


# ----------------------------------------


@app.route("/zapytaj", methods=["POST"])
def zapytaj():
    if container.wyszukiwarka is None:
        try:
            zaladuj_wyszukiwarke()
            inicjalizuj()
        except Exception as e:
            logger.exception("Blad inicjalizacji komponentow")
            error_details = get_error_details(e)
            return jsonify(
                {
                    "odpowiedz": f"❌ Błąd inicjalizacji: {e}",
                    "debug": (
                        error_details
                        if request.args.get("token") == ADMIN_TOKEN
                        else None
                    ),
                }
            ), 500

    dane = request.get_json(force=True)
    request_token = dane.get("token") or request.args.get("token")
    pytanie = dane.get("pytanie", "").strip()
    filtr_zrodlo = dane.get("zrodlo", "Wszystkie dokumenty")
    kontekst_tytul = dane.get("kontekst_tytul", None)  # poprzedni paragraf
    kontekst_pytanie = dane.get("kontekst_pytanie", None)  # poprzednie pytanie
    # print(f"DEBUG kontekst: tytul={kontekst_tytul}, pytanie={kontekst_pytanie}")
    logger.info(
        f"PYTANIE: {pytanie} | zrodlo: {filtr_zrodlo} | kontekst: {kontekst_tytul}"
    )

    if not pytanie:
        logger.warning("Puste pytanie od klienta")
        return jsonify({"blad": "Puste pytanie"}), 400

    try:
        from domain.services.ask_question import execute_ask_question

        payload = execute_ask_question(
            pytanie=pytanie,
            filtr_zrodlo=filtr_zrodlo,
            kontekst_tytul=kontekst_tytul,
            kontekst_pytanie=kontekst_pytanie,
            wyszukiwarka=container.wyszukiwarka,
            indeks_zdan=container.indeks_zdan,
            logger=logger,
            cache_get_fn=_cache_get,
            cache_set_fn=_cache_set,
            znajdz_rozszerzenie_fn=_znajdz_rozszerzenie,
            MAPA_ZNAKOW=MAPA_ZNAKOW,
            SYNONIMY=SYNONIMY,
        )
    except Exception as e:
        logger.exception("Błąd podczas przetwarzania zapytania")
        error_details = get_error_details(e)
        return jsonify(
            {
                "odpowiedz": f"❌ Błąd serwera: {e}",
                "debug": error_details if request_token == ADMIN_TOKEN else None,
            }
        ), 500

    return jsonify(payload)


@app.route("/admin/debug", methods=["GET"])
def admin_debug():
    token = request.args.get("token", "")
    info, status = execute_debug_info(DATA_DIR, PLIK_DB, ADMIN_TOKEN, token)
    return jsonify(info), status


@app.route("/feedback", methods=["POST"])
def feedback():
    dane = request.get_json(force=True)

    from domain.services.submit_feedback import execute_feedback_submission

    execute_feedback_submission(dane["pytanie_id"], dane["ocena"], BASE_DIR, logger)
    return jsonify({"ok": True})


@app.route("/graf_widok", methods=["GET"])
def graf_widok():
    """Otwiera kompletnie czysty plik nowego interfejsu (żeby nie pożerać wydajności asystenta)"""
    pytanie = request.args.get("pytanie", "")
    return render_template("graf.html", pytanie=pytanie)


@app.route("/graf_wektorowy", methods=["GET"])
def graf_wektorowy():
    """Zwraca graf słów (bigramy) lub graf paragrafów, zależnie od parametru ?tryb="""
    if not container.wyszukiwarka:
        return jsonify({"nodes": [], "edges": []})

    tryb = request.args.get("tryb", "slowa")
    if tryb == "paragrafy":
        return jsonify(container.wyszukiwarka.generuj_graf_paragrafow())
    else:
        return jsonify(container.wyszukiwarka.generuj_graf_slow(top_k=70))


@app.route("/zrodla", methods=["GET"])
def zrodla():
    """Zwraca listę dostępnych plików baz wiedzy z folderu /data."""
    import glob

    data_dir = os.path.join(BASE_DIR, "data")
    pliki = [
        os.path.basename(f)
        for f in glob.glob(os.path.join(data_dir, "*.json"))
        if not f.endswith("_cache.pkl")
    ]
    return jsonify(pliki)


@app.route("/historia", methods=["GET"])
def historia():
    try:
        inicjalizuj()
        return jsonify(pobierz_ostatnie_pytania(10))
    except Exception as e:
        logger.error(f"Błąd pobierania historii: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/admin/eksport_csv", methods=["GET"])
def admin_eksport_csv():
    from domain.services.admin_stats import execute_admin_eksport_csv

    return execute_admin_eksport_csv(request.args.get("token", ""), ADMIN_TOKEN)


@app.route("/admin")
def admin():
    token = request.args.get("token", "")

    if token != ADMIN_TOKEN:
        return (
            "Brak dostępu! Podaj prawidłowy token w adresie, np: /admin?token=dev-token-zmien-mnie",
            403,
        )
    return render_template("admin.html", stats=pobierz_statystyki(), token=token)


@app.route("/admin/dodaj_synonim", methods=["POST"])
def admin_dodaj_synonim():
    from domain.services.admin_stats import execute_admin_dodaj_synonim

    payload, status = execute_admin_dodaj_synonim(
        request.get_json(force=True), ADMIN_TOKEN, SYNONIMY, logger
    )
    return jsonify(payload), status


if __name__ != "__main__":
    try:
        inicjalizuj()
        zaladuj_wyszukiwarke()
    except Exception as e:
        logger.warning(f"Start w trybie WSGI bez pelnej inicjalizacji: {e}")


# ── start ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Inicjalizacja bazy danych...")
    inicjalizuj()
    print("Ladowanie bazy wiedzy...")
    zaladuj_wyszukiwarke()
    print(f"Serwer startuje -> http://localhost:{FLASK_PORT}\n")
    app.run(debug=FLASK_DEBUG, use_reloader=False, host=FLASK_HOST, port=FLASK_PORT)
