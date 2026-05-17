import os
import sys

# W Pythonie 3.11+ tomllib jest w bibliotece standardowej
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        print(
            "Błąd: Dla Pythona < 3.11 wymagana jest biblioteka 'tomli'. Zainstaluj ją przez 'pip install tomli'."
        )
        sys.exit(1)

# Centralna funkcja upraszczania znaków (analogiczna do usun_polskie_znaki z wyszukiwarki)
POLSKIE_ZNAKI = {
    "ą": "a",
    "ć": "c",
    "ę": "e",
    "ł": "l",
    "ń": "n",
    "ó": "o",
    "ś": "s",
    "ź": "z",
    "ż": "z",
    "Ą": "a",
    "Ć": "c",
    "Ę": "e",
    "Ł": "l",
    "Ń": "n",
    "Ó": "o",
    "Ś": "s",
    "Ź": "z",
    "Ż": "z",
}


def usun_polskie_znaki(tekst: str) -> str:
    return "".join(POLSKIE_ZNAKI.get(c, c) for c in tekst)


def waliduj_slowniki():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(base_dir)

    plik_synonimow = os.path.join(root_dir, "data", "synonimy.toml")
    plik_rozszerzen = os.path.join(root_dir, "data", "rozszerzenia.toml")

    bledy = []

    print("=== Uruchamiam Walidację Spójności Słowników ===")

    # 1. Sprawdzenie istnienia plików
    for plik in [plik_synonimow, plik_rozszerzen]:
        if not os.path.exists(plik):
            bledy.append(f"Plik słownika nie istnieje: {plik}")

    if bledy:
        wypisz_bledy_i_wyjdz(bledy)

    # 2. Parsowanie TOML
    try:
        with open(plik_synonimow, "rb") as f:
            synonimy = tomllib.load(f)
        print("  [OK] synonimy.toml załadowany pomyślnie.")
    except Exception as e:
        bledy.append(f"Błąd składni w synonimy.toml: {e}")
        synonimy = {}

    try:
        with open(plik_rozszerzen, "rb") as f:
            rozszerzenia = tomllib.load(f)
        print("  [OK] rozszerzenia.toml załadowany pomyślnie.")
    except Exception as e:
        bledy.append(f"Błąd składni w rozszerzenia.toml: {e}")
        rozszerzenia = {}

    if bledy:
        wypisz_bledy_i_wyjdz(bledy)

    # 3. Walidacja formatu kluczy i wartości w synonimy.toml
    print("Walidacja kluczy i wartości w synonimy.toml...")
    for k, v in synonimy.items():
        if not isinstance(k, str) or not k.strip():
            bledy.append(f"synonimy.toml: Klucz '{k}' musi być niepustym stringiem.")
            continue
        if not isinstance(v, str) or not v.strip():
            bledy.append(
                f"synonimy.toml: Wartość dla klucza '{k}' musi być niepustym stringiem."
            )
            continue

        # Sprawdzenie czy klucz jest znormalizowany (małe litery, brak polskich znaków)
        normal_k = usun_polskie_znaki(k.lower()).strip()
        if k != normal_k:
            bledy.append(
                f"synonimy.toml: Klucz '{k}' nie jest znormalizowany! Powinien brzmieć: '{normal_k}'."
            )

    # 4. Walidacja formatu kluczy i wartości w rozszerzenia.toml
    print("Walidacja kluczy i wartości w rozszerzenia.toml...")
    for k, v in rozszerzenia.items():
        if not isinstance(k, str) or not k.strip():
            bledy.append(
                f"rozszerzenia.toml: Klucz '{k}' musi być niepustym stringiem."
            )
            continue
        if not isinstance(v, str) or not v.strip():
            bledy.append(
                f"rozszerzenia.toml: Wartość dla klucza '{k}' musi być niepustym stringiem."
            )
            continue

        # Sprawdzenie czy klucz jest znormalizowany (małe litery, brak polskich znaków)
        normal_k = usun_polskie_znaki(k.lower()).strip()
        if k != normal_k:
            bledy.append(
                f"rozszerzenia.toml: Klucz '{k}' nie jest znormalizowany! Powinien brzmieć: '{normal_k}'."
            )

    # 5. Wykrywanie cykli i wieloetapowych łańcuchów w synonimy.toml
    print("Wyszukiwanie cykli i łańcuchów normalizacji w synonimy.toml...")
    for k in synonimy.keys():
        path = [k]
        curr = k
        cycle_detected = False

        while curr in synonimy:
            next_val = synonimy[curr]

            # Pętla własna (samoodwołanie, np. komisyjny -> komisyjny) - dopuszczalna/redundantna
            if next_val == curr:
                break

            # Wykrycie cyklu
            if next_val in path:
                cycle_detected = True
                bledy.append(
                    f"CRITICAL: Wykryto cykl w synonimach! {' -> '.join(path)} -> {next_val}"
                )
                break

            path.append(next_val)
            curr = next_val

        if cycle_detected:
            continue

        # Wykrycie łańcucha normalizacji (A -> B i B -> C, gdzie B != C)
        if len(path) > 2:
            bledy.append(
                f"ERROR: Wykryto wieloetapowy łańcuch normalizacji: {' -> '.join(path)}. "
                f"Ponieważ normalizacja działa w jednym kroku, powinieneś zmapować bezpośrednio: "
                f"'{path[0]}' = '{path[-1]}'."
            )

    # Podsumowanie walidacji
    if bledy:
        wypisz_bledy_i_wyjdz(bledy)
    else:
        print("\n=======================================================")
        print("  [SUKCES] Wszystkie słowniki są spójne i poprawne!")
        print("=======================================================")
        sys.exit(0)


def wypisz_bledy_i_wyjdz(bledy):
    print("\n=======================================================")
    print(f"  [BŁĄD] Wykryto {len(bledy)} błędów spójności słowników:")
    print("=======================================================")
    for błąd in bledy:
        print(f"  * {błąd}")
    print("=======================================================\n")
    sys.exit(1)


if __name__ == "__main__":
    waliduj_slowniki()
