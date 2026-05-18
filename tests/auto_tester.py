"""
auto_tester.py – automatyczne testowanie + analiza błędów przez Gemini

Gemini generuje pytania → twój model odpowiada → Gemini ocenia
→ Gemini analizuje błędy → sugeruje konkretne poprawki do ROZSZERZENIA_ZAPYTAN

Wymagania:
    pip install google-generativeai python-dotenv

Klucz API Gemini (darmowy): https://aistudio.google.com/app/apikey
Ustaw w pliku .env:  GEMINI_API_KEY=twój_klucz
"""

import json
import os
import re
import sys
import time
import tomllib

_prompts_cache = None


def pobierz_prompty() -> dict:
    global _prompts_cache
    if _prompts_cache is not None:
        return _prompts_cache

    sciezka = os.path.join(os.path.dirname(__file__), "prompts.toml")
    if not os.path.exists(sciezka):
        sciezka = "tests/prompts.toml"

    if os.path.exists(sciezka):
        try:
            with open(sciezka, "rb") as f:
                _prompts_cache = tomllib.load(f)
        except Exception:
            pass

    if _prompts_cache is None:
        _prompts_cache = {
            "generation": {"prompt": "Jesteś studentem..."},
            "evaluation": {"prompt": "Oceń czy paragraf..."},
            "error_analysis": {"prompt": "Analizujesz błędy..."},
        }
    return _prompts_cache


# Ustawienie ścieżek przed importami lokalnymi
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from google import genai
except ImportError:
    print("Zainstaluj: pip install google-genai")
    sys.exit(1)

try:
    from dotenv import load_dotenv

    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False

# Importy lokalne (absolutne)
from infrastructure.knowledge_loader import utworz_wyszukiwarke  # type: ignore

if HAS_DOTENV:
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

# ── konfiguracja ──────────────────────────────────────────────
API_KEY = os.getenv("GEMINI_API_KEY", "")
if not API_KEY:
    print("Brak klucza API. Ustaw GEMINI_API_KEY w pliku .env")
    sys.exit(1)

klient = genai.Client(api_key=API_KEY)

BASE_DIR = PROJECT_ROOT
LOGS_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)  # Tworzy folder logs, jeśli nie istnieje

LICZBA_PYTAN = 6
PLIK_WYNIKOW = os.path.join(LOGS_DIR, "auto_test_wyniki.json")
PLIK_POPRAWEK = os.path.join(LOGS_DIR, "auto_test_poprawki.py")

# ── pomocnicze ────────────────────────────────────────────────


def zapytaj_gemini(prompt: str, proba=4) -> str:
    # Wymuszenie modelu, który ma odblokowane darmowe pule
    nazwa_modelu = "gemini-2.5-flash"

    for i in range(proba):
        try:
            # Opóźnienie zapobiegające spamowaniu API
            time.sleep(4)
            res = klient.models.generate_content(model=nazwa_modelu, contents=prompt)
            return (res.text or "").strip()

        except Exception as e:
            blad_str = str(e)

            # Jeśli model nie istnieje, przerywamy natychmiast
            if "404" in blad_str or "NOT_FOUND" in blad_str:
                print(f"  ⚠ Krytyczny błąd: Nie znaleziono modelu {nazwa_modelu}")
                raise

            if i < proba - 1:
                # Szuka dokładnego czasu blokady w błędzie
                match = re.search(r"retry in ([\d\.]+)s", blad_str)
                if match:
                    czas_czekania = float(match.group(1)) + 2.0
                    print(
                        f"  ⚠ Przekroczono limit zapytań (RPM). Czekam {czas_czekania:.1f}s..."
                    )
                    time.sleep(czas_czekania)
                else:
                    print("  ⚠ Nierozpoznany błąd blokady. Czekam 60s...")
                    time.sleep(60)
            else:
                raise
    raise RuntimeError("Nieoczekiwany koniec funkcji zapytaj_gemini")


def parsuj_json(tekst: str):
    if "```" in tekst:
        tekst = tekst.split("```")[1]
        if tekst.startswith("json"):
            tekst = tekst[4:]
    return json.loads(tekst.strip())


# ── kroki ─────────────────────────────────────────────────────


def generuj_pytania(baza: list, liczba: int) -> list:
    tytuły = [p["tytul"] for p in baza]
    prompty = pobierz_prompty()
    szablon = prompty["generation"]["prompt"]
    prompt = szablon.format(
        liczba=liczba,
        podzial=liczba // 3 if liczba >= 3 else 1,
        tytuly_json=json.dumps(tytuły, ensure_ascii=False),
    )

    tekst = zapytaj_gemini(prompt)
    return parsuj_json(tekst)


def ocen_odpowiedz(pytanie: str, tytul: str, podobienstwo: float) -> dict:
    prompty = pobierz_prompty()
    szablon = prompty["evaluation"]["prompt"]
    prompt = szablon.format(
        pytanie=pytanie,
        tytul=tytul,
        podobienstwo_procent=f"{podobienstwo * 100:.0f}",
    )

    try:
        tekst = zapytaj_gemini(prompt)
        return parsuj_json(tekst)
    except Exception as e:
        return {
            "trafny": False,
            "komentarz": f"błąd oceny: {e}",
            "oczekiwany_paragraf": None,
        }


def analizuj_bledy(bledy: list, baza: list) -> str:
    if not bledy:
        return ""

    kontekst = {}
    for b in bledy:
        oczekiwany = b.get("oczekiwany_paragraf", "")
        if oczekiwany:
            for p in baza:
                if oczekiwany.lower() in p["tytul"].lower():
                    kontekst[p["tytul"]] = p["tresc"][:300]
                    break

    prompty = pobierz_prompty()
    szablon = prompty["error_analysis"]["prompt"]
    prompt = szablon.format(
        bledy_json=json.dumps(bledy, ensure_ascii=False, indent=2),
        kontekst_json=json.dumps(kontekst, ensure_ascii=False, indent=2),
    )

    try:
        return zapytaj_gemini(prompt)
    except Exception as e:
        return f"# błąd analizy: {e}"


def zapisz_poprawki(poprawki_tekst: str, bledy: list):
    with open(PLIK_POPRAWEK, "a", encoding="utf-8") as f:
        f.write("# ============================================================\n")
        f.write("# SUGEROWANE POPRAWKI do ROZSZERZENIA w core/slowniki.py\n")
        f.write("# Wygenerowane automatycznie przez auto_tester.py\n")
        f.write("# Skopiuj potrzebne wpisy do słownika ROZSZERZENIA\n")
        f.write("# ============================================================\n\n")
        f.write("# Błędne pytania:\n")

        for b in bledy:
            f.write(f"#   ✗ '{b['pytanie']}'\n")
            f.write(f"#     → otrzymano:  '{b['otrzymano']}'\n")
            if b.get("oczekiwany_paragraf"):
                f.write(f"#     → oczekiwano: '{b['oczekiwany_paragraf']}'\n")
        f.write("\n# Sugerowane wpisy do ROZSZERZENIA:\n")
        f.write(poprawki_tekst)
        f.write("\n")


# ── główna funkcja ────────────────────────────────────────────


def uruchom():
    print("=" * 55)
    print("  AUTO-TESTER z analizą błędów")
    print("  Gemini + Asystent Regulaminowy PWr")
    print("=" * 55)

    PLIK_BAZY = os.path.join(BASE_DIR, "data", "baza_wiedzy.json")

    with open(PLIK_BAZY, encoding="utf-8") as f:
        baza = json.load(f)

    w = utworz_wyszukiwarke(PLIK_BAZY)

    print(f"\n📝 Generuję {LICZBA_PYTAN} pytań przez Gemini...")
    pytania = generuj_pytania(baza, LICZBA_PYTAN)
    print(f"   Wygenerowano {len(pytania)} pytań\n")

    wyniki = []
    bledy = []
    trafne = 0

    for i, pytanie in enumerate(pytania, 1):
        print(f"[{i}/{len(pytania)}] {pytanie}")

        rezultaty = w.szukaj(pytanie, n_wynikow=1)
        if not rezultaty:
            print("  → BRAK WYNIKÓW\n")
            bledy.append(
                {
                    "pytanie": pytanie,
                    "otrzymano": "BRAK",
                    "oczekiwany_paragraf": None,
                    "komentarz": "brak wyników",
                }
            )
            continue

        wynik = rezultaty[0]
        tytul = wynik.tytul
        podobienstwo = wynik.podobienstwo
        print(f"  → {tytul} ({podobienstwo * 100:.0f}%)")

        ocena = ocen_odpowiedz(pytanie, tytul, podobienstwo)

        if ocena.get("trafny"):
            trafne += 1
            print(f"  ✓ {ocena.get('komentarz', '')}\n")
        else:
            print(f"  ✗ {ocena.get('komentarz', '')}")
            if ocena.get("oczekiwany_paragraf"):
                print(f"    lepszy: {ocena['oczekiwany_paragraf']}\n")
            else:
                print()
            bledy.append(
                {
                    "pytanie": pytanie,
                    "otrzymano": tytul,
                    "oczekiwany_paragraf": ocena.get("oczekiwany_paragraf"),
                    "komentarz": ocena.get("komentarz"),
                }
            )

        wyniki.append(
            {
                "pytanie": pytanie,
                "paragraf": tytul,
                "podobienstwo": podobienstwo,
                "ocena": ocena,
            }
        )

    print("=" * 55)
    print(f"  WYNIKI: {trafne}/{len(pytania)} trafnych")
    print(f"  Trafność: {trafne / len(pytania) * 100:.0f}%")
    print("=" * 55)

    if bledy:
        print(f"\n🔍 Analizuję {len(bledy)} błędów przez Gemini...")
        poprawki = analizuj_bledy(bledy, baza)
        zapisz_poprawki(poprawki, bledy)
        print(f"💡 Sugerowane poprawki zapisane do: {PLIK_POPRAWEK}")
        print("   Otwórz plik i skopiuj wpisy do ROZSZERZENIA_ZAPYTAN\n")

    nowe_wyniki = {
        "czas": time.strftime("%Y-%m-%d %H:%M:%S"),
        "trafne": trafne,
        "total": len(pytania),
        "trafnosc_procent": round(trafne / len(pytania) * 100, 1),
        "bledy": bledy,
        "wyniki": wyniki,
    }

    wszystkie_wyniki = []

    if os.path.exists(PLIK_WYNIKOW):
        try:
            with open(PLIK_WYNIKOW, "r", encoding="utf-8") as f:
                stare_dane = json.load(f)
                if isinstance(stare_dane, list):
                    wszystkie_wyniki = stare_dane
                else:
                    wszystkie_wyniki = [stare_dane]
        except json.JSONDecodeError:
            pass

    wszystkie_wyniki.append(nowe_wyniki)

    with open(PLIK_WYNIKOW, "w", encoding="utf-8") as f:
        json.dump(wszystkie_wyniki, f, ensure_ascii=False, indent=2)

    print(f"📊 Pełne wyniki dopisane do: {PLIK_WYNIKOW}")


# print([m.name for m in klient.models.list()])

if __name__ == "__main__":
    uruchom()
