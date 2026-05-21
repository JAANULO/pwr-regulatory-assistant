"""
test.py – automatyczne testy wyszukiwarki
Uruchom: python test.py
Pytania testowe są w: data/config/testy.toml
"""

import os
import pathlib
import sys
import tomllib

try:
    from infrastructure.knowledge_loader import utworz_wyszukiwarke
except ImportError:
    # Fallback dla uruchamiania bezpośredniego z folderu tests/
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from infrastructure.knowledge_loader import utworz_wyszukiwarke


# ── Ładowanie pytań z testy.toml ──────────────────────────────────────────────

TESTY_TOML = (
    pathlib.Path(__file__).resolve().parents[1] / "data" / "config" / "testy.toml"
)

_SEKCJE = [
    "testy_latwe",
    "testy_trudne",
    "testy_regresyjne",
    "testy_p4_rozbudowane",
    "testy_p5_uzupelniajace",
    "testy_conversational",
]


def wczytaj_testy(
    sciezka: pathlib.Path = TESTY_TOML,
    sekcje: list[str] | None = None,
) -> list[tuple[str, str]]:
    """
    Wczytuje pary (pytanie, oczekiwany) z testy.toml.
    Parametr `sekcje` pozwala wybrać konkretne grupy testów.
    Domyślnie wczytuje wszystkie sekcje z _SEKCJE.
    """
    with sciezka.open("rb") as f:
        dane = tomllib.load(f)

    wybrane = sekcje if sekcje is not None else _SEKCJE
    testy: list[tuple[str, str]] = []
    for sekcja in wybrane:
        for wpis in dane.get(sekcja, []):
            testy.append((wpis["pytanie"], wpis["oczekiwany"]))
    return testy


# Zmienna globalna TESTY – wczytana z pliku, nie zakodowana na sztywno
TESTY = wczytaj_testy()


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--k1", type=float, default=None)
    parser.add_argument("--b", type=float, default=None)
    parser.add_argument("--syn", type=float, default=None)
    parser.add_argument("--threshold", type=float, default=None)
    parser.add_argument(
        "--sekcje",
        nargs="+",
        default=None,
        metavar="SEKCJA",
        help=f"Wybierz sekcje testów: {_SEKCJE}",
    )
    args, unknown = parser.parse_known_args()

    # Obsługa filtrowania sekcji z CLI
    testy = wczytaj_testy(sekcje=args.sekcje) if args.sekcje else TESTY

    virtual_params = {}
    if args.k1 is not None:
        virtual_params["bm25_k1"] = args.k1
    if args.b is not None:
        virtual_params["bm25_b"] = args.b
    if args.syn is not None:
        virtual_params["synonym_weight"] = args.syn
    if args.threshold is not None:
        virtual_params["confidence_threshold"] = args.threshold

    if not virtual_params:
        virtual_params = None
    else:
        print(f"Uruchamiam testy z parametrami wirtualnymi (CLI): {virtual_params}")

    # Użycie ścieżek bezwzględnych dla stabilności na Windows
    SKRYPT_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = os.path.dirname(SKRYPT_DIR)
    PLIK_BAZY = os.path.join(BASE_DIR, "data", "kb", "baza_wiedzy.json")

    if not os.path.exists(PLIK_BAZY):
        print(f"Blad: Nie znaleziono pliku bazy w {PLIK_BAZY}")
        return

    # Wymuszenie postawienia lokalnej Bazy Danych pod izolowane testy na GHA / Runners
    from core.bd import inicjalizuj

    inicjalizuj()

    w = utworz_wyszukiwarke(PLIK_BAZY)
    ok = 0
    bledy = []

    print(f"Rozpoczynam testy ({len(testy)} przypadkow)...")

    for pytanie, oczekiwany_fragment in testy:
        wyniki = w.szukaj(pytanie, n_wynikow=1, virtual_params=virtual_params)
        if not wyniki:
            bledy.append((pytanie, oczekiwany_fragment, "BRAK WYNIKOW"))
            continue

        tytul = wyniki[0].tytul
        if oczekiwany_fragment.lower() in tytul.lower():
            ok += 1
        else:
            bledy.append((pytanie, oczekiwany_fragment, tytul))

    print(f"\nWyniki: {ok}/{len(testy)} testow zaliczonych")

    if bledy:
        print("\nNiezaliczone:")
        for p, ocz, got in bledy:
            # Używamy bezpiecznych znaków ASCII zamiast Unicode
            print(f"  [X] '{p}'")
            print(f"      oczekiwano: '{ocz}'")
            print(f"      otrzymano:  '{got}'")
    else:
        print("Wszystkie testy zaliczone [OK]")


if __name__ == "__main__":
    # Wymuszenie UTF-8 dla strumieni wyjściowych na Windows
    if sys.platform == "win32":
        import io

        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    main()
