"""
weryfikacja.py – jednorazowy skrypt walidacji projektu
"""

import json
import os
import py_compile
import sys

# Ustawienie ścieżki dla modułów lokalnych
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.slowniki import ROZSZERZENIA, SYNONIMY
from core.wyszukiwarka import tokenizuj
from infrastructure.knowledge_loader import utworz_wyszukiwarke

print("=" * 55)
print("  WERYFIKACJA PROJEKTU")
print("=" * 55)

# 1. Baza wiedzy
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLIK_BAZY = os.path.join(BASE_DIR, "data", "baza_wiedzy.json")

baza = json.load(open(PLIK_BAZY, encoding="utf-8"))
print("\n[1] Baza wiedzy:")
print(f"    Paragrafow: {len(baza)}")
print(f"    Pola:       {list(baza[0].keys())}")
bez_tresci = [f["tytul"] for f in baza if not f.get("tresc")]
print(f"    Bez tresci: {len(bez_tresci)} {'OK' if not bez_tresci else 'BLAD'}")

# 2. Slowniki
print("\n[2] Slowniki:")
print(f"    Rozszerzen: {len(ROZSZERZENIA)}")
print(f"    Synonimow:  {len(SYNONIMY)}")

# 4. Wyszukiwarka
print("\n[4] Wyszukiwarka:")

# Ścieżka bezwzględna do bazy wiedzy
PLIK_BAZY = os.path.join(ROOT_DIR, "data", "baza_wiedzy.json")
w = utworz_wyszukiwarke(PLIK_BAZY)
print(
    f"    Metoda szukaj(zrodlo=): {'TAK' if 'zrodlo' in str(w.szukaj.__code__.co_varnames) else 'BRAK'}"
)
print(
    f"    generuj_graf_paragrafow: {'TAK' if hasattr(w, 'generuj_graf_paragrafow') else 'BRAK'}"
)
print(
    f"    generuj_graf_slow:       {'TAK' if hasattr(w, 'generuj_graf_slow') else 'BRAK'}"
)

wyniki_filtr = w.szukaj("egzamin", n_wynikow=2, zrodlo="nieistniejace.json")
print(
    f"    Filtr =nieistniejace.json: {len(wyniki_filtr)} wynikow (oczek. 0) {'OK' if len(wyniki_filtr) == 0 else 'BLAD'}"
)

wyniki_wszystkie = w.szukaj("egzamin", n_wynikow=2, zrodlo="Wszystkie dokumenty")
print(
    f"    Filtr =Wszystkie dokumenty: {len(wyniki_wszystkie)} wynikow (oczek. 2) {'OK' if len(wyniki_wszystkie) == 2 else 'BLAD'}"
)

graf = w.generuj_graf_paragrafow()
print(
    f"    Graf paragrafow: {len(graf['nodes'])} wezly, {len(graf['edges'])} krawedzie"
)

# 5. Payload check (czy app.py zwroci slowa_kluczowe)
tokeny = tokenizuj("ile razy mozna powtarzac egzamin")
print("\n[5] Tokenizacja pytania:")
print("    Input:  'ile razy mozna powtarzac egzamin'")
print(f"    Output: {tokeny}")
print(f"    OK: {len(tokeny) > 0}")

# 6. Kluczowe importy app.py
print("\n[6] Importy app.py:")
try:
    app_path = os.path.join(ROOT_DIR, "app.py")
    py_compile.compile(app_path, doraise=True)
    print("    Skladnia app.py: OK")
except py_compile.PyCompileError as e:
    print(f"    Skladnia app.py: BLAD - {e}")

# 7. Sprawdz czy main.js ma wyborZrodla i walidatorZrodla
print("\n[7] Frontend (main.js):")
js_path = os.path.join(ROOT_DIR, "static", "js", "main.js")
js_content = open(js_path, encoding="utf-8").read()
checks = [
    ("infoBazaWidzy", "Zarządzanie bazami (Modal)"),
    ("slowa_kluczowe", "Highlight slow kluczowych"),
]
for token, opis in checks:
    obecny = token in js_content
    print(f"    {opis}: {'OK' if obecny else 'BRAK'}")

# 8. PWA i Mobilność (PLAN 1.2)
print("\n[8] PWA i Mobilnosc (PLAN 1.2):")
manifest_path = os.path.join(ROOT_DIR, "static", "manifest.json")
index_path = os.path.join(ROOT_DIR, "templates", "index.html")

if os.path.exists(manifest_path):
    try:
        manifest_data = json.load(open(manifest_path, encoding="utf-8"))
        has_standalone = manifest_data.get("display") == "standalone"
        has_start_url = manifest_data.get("start_url") == "/"
        print(
            f"    manifest.json:  OK (display={manifest_data.get('display')}, start_url={manifest_data.get('start_url')})"
        )
        print(
            f"    Walidacja PWA:  {'OK' if (has_standalone and has_start_url) else 'BLAD'}"
        )
    except Exception as e:
        print(f"    manifest.json:  BLAD parsowania JSON - {e}")
else:
    print("    manifest.json:  BRAK PLIKU")

if os.path.exists(index_path):
    index_content = open(index_path, encoding="utf-8").read()
    has_link = 'rel="manifest"' in index_content
    print(f"    index.html link:{'OK' if has_link else 'BRAK linku manifestu'}")
else:
    print("    index.html:     BRAK PLIKU")

has_touch = (
    "touchstart" in js_content
    and "touchend" in js_content
    and "obsluzGestSwipe" in js_content
)
print(f"    Gesty dotykowe: {'OK' if has_touch else 'BRAK w main.js'}")

print("\n" + "=" * 55)
print("  KONIEC WERYFIKACJI")
print("=" * 55)
