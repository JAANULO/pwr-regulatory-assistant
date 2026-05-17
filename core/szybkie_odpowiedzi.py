"""
szybkie_odpowiedzi.py - Obsługa szybkich definicji ze słownika pojęć (§ 2 regulaminu).
Ładuje definicje dynamicznie z pliku TOML w folderze data/.
"""

import os
import re
import sys
from core.wyszukiwarka import usun_polskie_znaki

# W Pythonie 3.11+ tomllib jest częścią biblioteki standardowej
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        raise ImportError(
            "Dla wersji Pythona starszych niż 3.11 wymagana jest biblioteka 'tomli'."
        )


def _wczytaj_slownik_pojec() -> dict[str, str]:
    """
    Wczytuje słownik pojęć z pliku TOML i buduje płaską strukturę wariantów.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(base_dir)
    sciezka_pliku = os.path.join(root_dir, "data", "slownik.toml")

    if not os.path.exists(sciezka_pliku):
        raise FileNotFoundError(
            f"Krytyczny błąd: Plik słownika pojęć nie istnieje w lokalizacji: {os.path.abspath(sciezka_pliku)}"
        )

    try:
        with open(sciezka_pliku, "rb") as f:
            dane = tomllib.load(f)

        slownik = {}
        for klucz_sekcji, wpis in dane.items():
            definicja = wpis.get("definicja", "")
            warianty = wpis.get("warianty", [])
            for var in warianty:
                slownik[str(var).strip().lower()] = str(definicja)
        return slownik
    except Exception as e:
        raise RuntimeError(
            f"Krytyczny błąd podczas parsowania słownika pojęć TOML ({sciezka_pliku}): {e}"
        )


# Inicjalizacja słownika pojęć (ładowana jednorazowo przy imporcie modułu)
SLOWNIK_POJEC = _wczytaj_slownik_pojec()

SYGNALY_PREFIX = [
    "co to jest",
    "co to sa",
    "co to za",
    "co to",
    "co oznacza",
    "czym jest",
    "czym sa",
    "kim jest",
    "kto to",
    "wyjasnij",
    "definicja",
    "znaczenie",
    "wyjasnij pojecie",
    "co rozumie sie przez pojecie",
    "co to wlasciwie jest",
    "powiedz mi co to",
    "pojecie",
    "okreslenie",
    "slowo",
    "zwrot",
]

MODYFIKATORY_SUFFIX = [
    "w rozumieniu regulaminu",
    "w regulaminie",
    "na studiach",
    "w regulaminie studiow",
    "studiow",
    "regulaminu",
    "pojecie",
    "okreslenie",
    "slowo",
]


def oczysc_do_podmiotu(pyt_norm: str) -> str:
    """
    Ekstrahuje główny podmiot zapytania definicyjnego poprzez usunięcie
    powszechnych prefiksów pytających oraz sufiksów modyfikujących w pętli.
    """
    # 1. Usuwanie prefiksów w pętli
    zmieniono = True
    while zmieniono:
        zmieniono = False
        for pref in SYGNALY_PREFIX:
            if pyt_norm.startswith(pref):
                pyt_norm = pyt_norm[len(pref) :].strip()
                zmieniono = True
                break

    # 2. Usuwanie sufiksów w pętli
    zmieniono = True
    while zmieniono:
        zmieniono = False
        for suff in MODYFIKATORY_SUFFIX:
            if pyt_norm.endswith(suff):
                pyt_norm = pyt_norm[: -len(suff)].strip()
                zmieniono = True
                break

    # 3. Usuwanie pojedynczych słów pomocniczych na początku i na końcu
    pyt_norm = re.sub(r"\b(jest|sa|za|pod|przez|o|w|na|dla|to)\b", "", pyt_norm).strip()
    return pyt_norm


def dopasuj_szybka_odpowiedz(pytanie: str) -> str | None:
    """
    Weryfikuje, czy pytanie dotyczy definicji jednego z pojęć z § 2.
    Jeśli tak, zwraca bezbłędną zrekonstruowaną definicję.
    """
    pyt_norm = usun_polskie_znaki(pytanie.lower().strip().rstrip("?!"))

    # Sprawdzamy obecność jawnego sygnału pytania o definicję
    jest_zapytanie_definicji = any(sygnal in pyt_norm for sygnal in SYGNALY_PREFIX)

    # Jeśli brak jawnego sygnału, sprawdzamy czy zapytanie jest bardzo krótkie (1-2 słowa)
    if not jest_zapytanie_definicji:
        slowa = pyt_norm.split()
        if len(slowa) <= 2:
            jest_zapytanie_definicji = True

    if not jest_zapytanie_definicji:
        return None

    # Sortujemy klucze od najdłuższych
    posortowane_klucze = sorted(SLOWNIK_POJEC.keys(), key=len, reverse=True)

    # --- KROK 1: Szybkie dopasowanie fraz wielowyrazowych (brak ryzyka fałszywych dopasowań) ---
    for klucz in posortowane_klucze:
        if len(klucz.split()) > 1:
            szablon = rf"\b{re.escape(klucz)}\b"
            if re.search(szablon, pyt_norm):
                return SLOWNIK_POJEC[klucz]

    # --- KROK 2: Precyzyjne dopasowanie jednowyrazowych pojęć (z oczyszczaniem do podmiotu) ---
    podmiot = oczysc_do_podmiotu(pyt_norm)
    if not podmiot:
        return None

    for klucz in posortowane_klucze:
        if len(klucz.split()) == 1:
            # Dokładne dopasowanie oczyszczonego podmiotu
            if podmiot == klucz:
                return SLOWNIK_POJEC[klucz]

            # Tolerancja na literówki (Levenshtein 1 dla słów >= 4 znaków)
            if len(klucz) >= 4 and len(podmiot) >= 4:
                from core.wyszukiwarka import levenshtein

                if levenshtein(podmiot, klucz) <= 1:
                    return SLOWNIK_POJEC[klucz]

    return None
