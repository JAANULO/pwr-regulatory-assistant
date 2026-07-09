"""
slowniki.py - centralne miejsce dla synonimów i rozszerzeń zapytań.
Ładuje słowniki dynamicznie z plików TOML w folderze data/.
"""

import logging
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
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)

PLIK_SYNONIMOW = os.path.join(ROOT_DIR, "data", "config", "synonimy.toml")
PLIK_ROZSZERZEN = os.path.join(ROOT_DIR, "data", "config", "rozszerzenia.toml")
PLIK_ROZSZERZEN_ZDAN = os.path.join(
    ROOT_DIR, "data", "config", "rozszerzenia_zdan.toml"
)


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


class DynamicDictProxy(dict):
    """
    Proxy słownika automatycznie przeładowujące dane z pliku TOML
    przy wykryciu zmiany czasu modyfikacji (mtime).
    """

    def __init__(self, sciezka_pliku: str):
        super().__init__()
        self.sciezka_pliku = sciezka_pliku
        self._mtime = 0.0
        self._sprawdz_i_przeladuj()

    def _sprawdz_i_przeladuj(self) -> None:
        if not os.path.exists(self.sciezka_pliku):
            return
        try:
            current_mtime = os.path.getmtime(self.sciezka_pliku)
            if current_mtime > self._mtime:
                dane = _wczytaj_slownik_toml(self.sciezka_pliku)
                self.clear()
                self.update(dane)
                self._mtime = current_mtime
        except Exception as e:
            logger.warning(
                "Nie udało się przeładować słownika %s: %s",
                self.sciezka_pliku,
                e,
            )

    def __getitem__(self, key):
        self._sprawdz_i_przeladuj()
        return super().__getitem__(key)

    def __contains__(self, item):
        self._sprawdz_i_przeladuj()
        return super().__contains__(item)

    def get(self, key, default=None):
        self._sprawdz_i_przeladuj()
        return super().get(key, default)

    def items(self):
        self._sprawdz_i_przeladuj()
        return super().items()

    def keys(self):
        self._sprawdz_i_przeladuj()
        return super().keys()

    def values(self):
        self._sprawdz_i_przeladuj()
        return super().values()

    def __len__(self):
        self._sprawdz_i_przeladuj()
        return super().__len__()

    def __iter__(self):
        self._sprawdz_i_przeladuj()
        return super().__iter__()

    def __repr__(self):
        self._sprawdz_i_przeladuj()
        return super().__repr__()


# Inicjalizacja globalnych słowników z dynamicznym ładowaniem
SYNONIMY = DynamicDictProxy(PLIK_SYNONIMOW)
ROZSZERZENIA = DynamicDictProxy(PLIK_ROZSZERZEN)
ROZSZERZENIA_ZDAN = DynamicDictProxy(PLIK_ROZSZERZEN_ZDAN)
