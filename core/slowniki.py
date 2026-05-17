"""
slowniki.py - centralne miejsce dla synonimów i rozszerzeń zapytań.
Ładuje słowniki dynamicznie z plików TOML w folderze data/.
"""

import os
import sys

# W Pythonie 3.11+ tomllib jest częścią biblioteki standardowej
if sys.version_info >= (3, 11):
    import tomllib
else:
    # Wygodny fallback na wypadek starszych wersji
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        raise ImportError(
            "Dla wersji Pythona starszych niż 3.11 wymagana jest biblioteka 'tomli'."
        )

# Ustalenie ścieżek bezwzględnych do plików słowników
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)

PLIK_SYNONIMOW = os.path.join(ROOT_DIR, "data", "synonimy.toml")
PLIK_ROZSZERZEN = os.path.join(ROOT_DIR, "data", "rozszerzenia.toml")


def _wczytaj_slownik_toml(sciezka_pliku: str) -> dict[str, str]:
    """
    Wczytuje płaski słownik z pliku TOML.
    W przypadku błędu składni lub braku pliku rzuca czytelny wyjątek.
    """
    if not os.path.exists(sciezka_pliku):
        raise FileNotFoundError(
            f"Krytyczny błąd: Plik słownika nie istnieje w lokalizacji: {os.path.abspath(sciezka_pliku)}"
        )

    try:
        with open(sciezka_pliku, "rb") as f:
            dane = tomllib.load(f)
            # Upewniamy się, że klucze i wartości są łańcuchami znaków
            return {str(k): str(v) for k, v in dane.items()}
    except Exception as e:
        raise RuntimeError(
            f"Krytyczny błąd podczas parsowania słownika TOML ({sciezka_pliku}): {e}"
        )


# Inicjalizacja globalnych słowników (ładowana jednorazowo przy imporcie modułu)
SYNONIMY = _wczytaj_slownik_toml(PLIK_SYNONIMOW)
ROZSZERZENIA = _wczytaj_slownik_toml(PLIK_ROZSZERZEN)
