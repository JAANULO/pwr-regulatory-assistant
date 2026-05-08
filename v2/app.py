"""
app.py – serwer Flask dla asystenta regulaminowego PWr
Uruchomienie: python app.py
Adres:        http://localhost:5000
"""

import logging
import os
import re
import sys
import time
from collections import OrderedDict
from typing import TYPE_CHECKING

# Ustawienie ścieżki dla modułów lokalnych
v2_root = os.path.abspath(os.path.dirname(__file__))
if v2_root not in sys.path:
    sys.path.insert(0, v2_root)

from flask import Flask, jsonify, render_template, request

from core.settings import (
    ADMIN_TOKEN,
    FLASK_DEBUG,
    FLASK_HOST,
    FLASK_PORT,
    LOG_LEVEL,
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

if TYPE_CHECKING:
    from core.indeks_zdan import IndeksZdan


def _znajdz_rozszerzenie(pytanie_lower: str) -> str:
    """Zwraca rozszerzenie dla pierwszej pasującej frazy lub pusty string."""
    for fraza, rozszerzenie in ROZSZERZENIA.items():
        if fraza in pytanie_lower:
            return rozszerzenie
    return ""


def _wykryj_numer_paragrafu(pytanie: str) -> str | None:
    """Wykrywa numer paragrafu z zapytania (np. §18, paragraf 18)."""
    pytanie_ascii = pytanie.lower().translate(MAPA_ZNAKOW)
    dopasowanie = re.search(
        r"(?:§\s*|paragraf(?:ie|u|em|owi|ach)?\s+)(\d+)", pytanie_ascii
    )
    return dopasowanie.group(1) if dopasowanie else None


def _cache_get(pytanie: str):
    wpis = CACHE_ODPOWIEDZI.get(pytanie)
    if not wpis:
        return None
    if time.time() - wpis["ts"] > CACHE_TTL_SECONDS:
        CACHE_ODPOWIEDZI.pop(pytanie, None)
        return None
    return wpis["data"]


def _cache_set(pytanie: str, odpowiedz: dict):
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

logger = logging.getLogger("asystent")
logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
logger.propagate = False  # nie przepuszczaj do root loggera
logging.getLogger("werkzeug").setLevel(logging.WARNING)

# ── ładowanie wyszukiwarki raz przy starcie ───────────────────────────────────
wyszukiwarka: Wyszukiwarka | None = None
indeks_zdan: "IndeksZdan | None" = None


def zaladuj_wyszukiwarke():
    global wyszukiwarka
    if not os.path.isdir(DATA_DIR):
        raise FileNotFoundError(f"Brak katalogu '{DATA_DIR}'.")

    os.makedirs(os.path.dirname(PLIK_LOG), exist_ok=True)

    if not logger.handlers:
        fh = logging.FileHandler(PLIK_LOG, encoding="utf-8")
        fh.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
            )
        )
        logger.addHandler(fh)

    from infrastructure.knowledge_loader import (
        utworz_wyszukiwarke,
        utworz_indeks_zdan,
    )

    wyszukiwarka = utworz_wyszukiwarke(DATA_DIR)
    global indeks_zdan
    indeks_zdan = utworz_indeks_zdan(DATA_DIR)
    logger.info("Wyszukiwarka zaladowana")


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
    if wyszukiwarka is None:
        return jsonify({"blad": "Wyszukiwarka nie załadowana"}), 500

    from domain.services.simulate_question import execute_simulate_question

    payload, status = execute_simulate_question(
        request.get_json(force=True), wyszukiwarka, logger
    )
    return jsonify(payload), status


# ----------------------------------------


@app.route("/zapytaj", methods=["POST"])
def zapytaj():
    if wyszukiwarka is None:
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
            wyszukiwarka=wyszukiwarka,
            indeks_zdan=indeks_zdan,
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
    if not wyszukiwarka:
        return jsonify({"nodes": [], "edges": []})

    tryb = request.args.get("tryb", "slowa")
    if tryb == "paragrafy":
        return jsonify(wyszukiwarka.generuj_graf_paragrafow())
    else:
        return jsonify(wyszukiwarka.generuj_graf_slow(top_k=70))


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
    print("Ladowanie bazy wiedzy...")
    zaladuj_wyszukiwarke()
    print(f"Serwer startuje -> http://localhost:{FLASK_PORT}\n")
    app.run(debug=FLASK_DEBUG, use_reloader=False, host=FLASK_HOST, port=FLASK_PORT)
