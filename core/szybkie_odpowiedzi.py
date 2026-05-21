"""
szybkie_odpowiedzi.py - Obsługa szybkich definicji ze słownika pojęć (§ 2 regulaminu).
Ładuje definicje dynamicznie z pliku TOML w folderze data/.
"""

import os
import re
import sys
from typing import Any
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
    sciezka_pliku = os.path.join(root_dir, "data", "config", "slownik.toml")

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

_cfg_szybkie_cache: dict[str, list[str]] | None = None
_cfg_szybkie_mtime: float = 0.0


def pobierz_konfiguracje_szybkich_odpowiedzi() -> dict[str, Any]:
    global _cfg_szybkie_cache, _cfg_szybkie_mtime
    sciezka = os.path.join(
        os.path.dirname(__file__), "..", "data", "config", "szybkie_odpowiedzi.toml"
    )
    if not os.path.exists(sciezka):
        sciezka = os.path.join("data", "config", "szybkie_odpowiedzi.toml")

    if not os.path.exists(sciezka):
        raise FileNotFoundError(
            f"Krytyczny błąd: Plik konfiguracji szybkich odpowiedzi nie istnieje w lokalizacji: {os.path.abspath(sciezka)}"
        )

    try:
        mtime = os.path.getmtime(sciezka)
        if _cfg_szybkie_cache is None or mtime > _cfg_szybkie_mtime:
            with open(sciezka, "rb") as f:
                _cfg_szybkie_cache = tomllib.load(f)
            _cfg_szybkie_mtime = mtime
    except Exception as e:
        if _cfg_szybkie_cache is None:
            raise RuntimeError(
                f"Krytyczny błąd podczas wczytywania konfiguracji szybkich odpowiedzi TOML ({sciezka}): {e}"
            )

    return _cfg_szybkie_cache


def oczysc_do_podmiotu(pyt_norm: str) -> str:
    """
    Ekstrahuje główny podmiot zapytania definicyjnego poprzez usunięcie
    powszechnych prefiksów pytających oraz sufiksów modyfikujących w pętli.
    """
    cfg_szybkie = pobierz_konfiguracje_szybkich_odpowiedzi()
    sygnaly_prefix = cfg_szybkie.get("sygnaly_prefix", [])
    modyfikatory_suffix = cfg_szybkie.get("modyfikatory_suffix", [])

    # 1. Usuwanie prefiksów w pętli
    zmieniono = True
    while zmieniono:
        zmieniono = False
        for pref in sygnaly_prefix:
            if pyt_norm.startswith(pref):
                pyt_norm = pyt_norm[len(pref) :].strip()
                zmieniono = True
                break

    # 2. Usuwanie sufiksów w pętli
    zmieniono = True
    while zmieniono:
        zmieniono = False
        for suff in modyfikatory_suffix:
            if pyt_norm.endswith(suff):
                pyt_norm = pyt_norm[: -len(suff)].strip()
                zmieniono = True
                break

    # 3. Usuwanie pojedynczych słów pomocniczych na początku i na końcu
    slowa_czyszczenia = cfg_szybkie.get("czyszczenie_podmiotu", {}).get("slowa", [])
    if slowa_czyszczenia:
        wzorzec = r"\b(" + "|".join(re.escape(s) for s in slowa_czyszczenia) + r")\b"
        pyt_norm = re.sub(wzorzec, "", pyt_norm).strip()
    return pyt_norm


def dopasuj_szybka_odpowiedz(pytanie: str) -> str | None:
    """
    Weryfikuje, czy pytanie dotyczy definicji jednego z pojęć z § 2.
    Jeśli tak, zwraca bezbłędną zrekonstruowaną definicję.
    """
    from core.wyszukiwarka import pobierz_konfiguracje

    cfg = pobierz_konfiguracje()
    cfg_slownik = cfg.get("slownik_pojec", {})
    min_dlugosc_korekty = cfg_slownik.get("min_dlugosc_korekty", 4)
    max_dystans_levenshteina = cfg_slownik.get("max_dystans_levenshteina", 1)

    pyt_norm = usun_polskie_znaki(pytanie.lower().strip().rstrip("?!"))

    cfg_szybkie = pobierz_konfiguracje_szybkich_odpowiedzi()
    sygnaly_prefix = cfg_szybkie.get("sygnaly_prefix", [])

    # Sprawdzamy obecność jawnego sygnału pytania o definicję
    jest_zapytanie_definicji = any(sygnal in pyt_norm for sygnal in sygnaly_prefix)

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

            # Tolerancja na literówki (Levenshtein)
            if (
                len(klucz) >= min_dlugosc_korekty
                and len(podmiot) >= min_dlugosc_korekty
            ):
                from core.wyszukiwarka import levenshtein

                if levenshtein(podmiot, klucz) <= max_dystans_levenshteina:
                    return SLOWNIK_POJEC[klucz]

    return None
