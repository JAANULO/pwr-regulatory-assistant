"""
symulacja.py – automatyczna optymalizacja parametrów z config.toml
Wyciąga pytania testowe z data/config/testy.toml, buduje siatkę parametrów liczbowych,
uruchamia grid-search i zapisuje optymalną konfigurację.

Użycie standalone:
    python scripts/symulacja.py

Użycie z Flask:
    from scripts.symulacja import run_grid_search
    result = run_grid_search()
"""

import itertools
import json
import pathlib
import random
import sys
import tomllib
from typing import Any, Iterator

# Zapewnienie importów z katalogu głównego projektu
ROOT_DIR = str(pathlib.Path(__file__).resolve().parents[1])
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# GŁÓWNY PARAMETR SYMULACJI - Ilość sprawdzanych kombinacji
# Im większa wartość, tym dłużej trwa symulacja, ale szansa na lepszy wynik rośnie.
DOMYSLNA_LICZBA_KOMBINACJI = 100


# ── 1. Wyciąganie pytań z testy.toml ────────────────────────────────────────


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


def load_questions(
    path: str | None = None,
    sekcje: list[str] | None = None,
) -> list[tuple[str, str, str]]:
    """
    Wczytuje trójki (pytanie, oczekiwany, oczekiwany_punkt) z testy.toml.

    Jeśli path podano → wczytuje z zewnętrznego pliku TOML lub TXT.
      - TOML: obsługuje ten sam format co testy.toml (sekcje z [[...]])
      - TXT:  jedno pytanie na linię (oczekiwany = "" – accuracy nie będzie liczona)
    Inaczej → wczytuje z data/config/testy.toml.

    Parametr `sekcje` pozwala wybrać konkretne grupy (np. ["testy_trudne"]).
    """
    if path:
        p = pathlib.Path(path)
        if not p.is_file():
            raise FileNotFoundError(f"Plik z pytaniami nie istnieje: {path}")
        if p.suffix == ".toml":
            with p.open("rb") as f:
                dane = tomllib.load(f)
            wybrane = sekcje if sekcje is not None else _SEKCJE
            pary: list[tuple[str, str, str]] = []
            for sekcja in wybrane:
                for wpis in dane.get(sekcja, []):
                    pary.append(
                        (
                            wpis["pytanie"],
                            wpis.get("oczekiwany", ""),
                            wpis.get("oczekiwany_punkt", ""),
                        )
                    )
            return pary
        else:
            # Tryb TXT (wsteczna kompatybilność): brak info o oczekiwanym paragrafie
            linie = [
                l.strip()
                for l in p.read_text(encoding="utf-8").splitlines()
                if l.strip()
            ]
            return [(q, "", "") for q in linie]

    # Domyślnie: wczytaj z testy.toml
    with TESTY_TOML.open("rb") as f:
        dane = tomllib.load(f)
    wybrane = sekcje if sekcje is not None else _SEKCJE
    pary = []
    for sekcja in wybrane:
        for wpis in dane.get(sekcja, []):
            pary.append(
                (
                    wpis["pytanie"],
                    wpis.get("oczekiwany", ""),
                    wpis.get("oczekiwany_punkt", ""),
                )
            )
    return pary


# ── 2. Konfiguracja – spłaszczanie / odspłaszczanie ─────────────────────────


CONFIG_PATH = (
    pathlib.Path(__file__).resolve().parents[1] / "data" / "config" / "config.toml"
)

# Sekcje, które NIE są parametrami liczbowymi do optymalizacji
_SKIP_SECTIONS = frozenset(
    [
        "szumy_i_wykluczenia",
        "komunikaty_serwera",
        "naglowki_csv",
    ]
)


def _flatten_numeric(cfg: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """
    Spłaszcza config TOML do formatu {"bm25.k1": 1.5, ...}.
    Bierze TYLKO wartości int/float.  Pomija sekcje z _SKIP_SECTIONS.
    Pomija wartości zagnieżdżone w dict z kluczem 'token' (mapa_wag_dynamiczna).
    """
    flat: dict[str, Any] = {}
    for k, v in cfg.items():
        key = f"{prefix}.{k}" if prefix else k
        if k in _SKIP_SECTIONS:
            continue
        if isinstance(v, dict):
            # mapa_wag_dynamiczna → wartości to {"token": ..., "mnoznik": ...}
            if "token" in v and "mnoznik" in v:
                flat[f"{key}.mnoznik"] = v["mnoznik"]
            else:
                flat.update(_flatten_numeric(v, key))
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            flat[key] = v
    return flat


def _unflatten(flat: dict[str, Any]) -> dict[str, Any]:
    """Odwraca spłaszczanie."""
    result: dict[str, Any] = {}
    for compound_key, value in flat.items():
        parts = compound_key.split(".")
        d = result
        for part in parts[:-1]:
            d = d.setdefault(part, {})
        d[parts[-1]] = value
    return result


def load_base_config() -> dict[str, Any]:
    with CONFIG_PATH.open("rb") as f:
        return tomllib.load(f)


# ── 3. Generowanie siatki parametrów ─────────────────────────────────────────


def _generate_param_grid(
    flat_cfg: dict[str, Any],
) -> Iterator[dict[str, Any]]:
    """
    Dla każdego parametru liczbowego generuje warianty:
      int  → [v-step, v, v+step]
      float → [v*0.8, v, v*1.2]  (zaokrąglone do 3 miejsc)
    Zwraca generator iloczynu kartezjańskiego (lazy – nie ładuje do RAM od razu).
    """
    param_options: list[tuple[str, list[Any]]] = []

    for key, val in flat_cfg.items():
        if isinstance(val, int):
            step_int = max(1, abs(val) // 5)
            param_options.append((key, sorted({val - step_int, val, val + step_int})))
        elif isinstance(val, float):
            step_float = max(0.05, abs(val) * 0.2)
            param_options.append(
                (
                    key,
                    sorted(
                        {
                            round(val - step_float, 3),
                            round(val, 3),
                            round(val + step_float, 3),
                        }
                    ),
                )
            )

    if not param_options:
        # Zwracamy jeden pusty kombos
        return iter([{}])

    keys = [k for k, _ in param_options]
    values = [opts for _, opts in param_options]

    def _combo_gen():
        for combo_vals in itertools.product(*values):
            yield dict(zip(keys, combo_vals))

    return _combo_gen()  # type: ignore[return-value]


def _count_combinations(flat_cfg: dict[str, Any]) -> int:
    """Liczy liczbę kombinacji bez generowania ich w pamięci."""
    total = 1
    for val in flat_cfg.values():
        if isinstance(val, int):
            step_int = max(1, abs(val) // 5)
            total *= len({val - step_int, val, val + step_int})
        elif isinstance(val, float):
            step_float = max(0.05, abs(val) * 0.2)
            total *= len(
                {round(val - step_float, 3), round(val, 3), round(val + step_float, 3)}
            )
    return total


# ── 4. Ocena jednej konfiguracji ─────────────────────────────────────────────


def _build_virtual_params(flat_combo: dict[str, Any]) -> dict[str, Any]:
    """
    Przekłada spłaszczone klucze konfiguracji na klucze rozumiane
    przez Wyszukiwarka.szukaj(virtual_params=...).

    Obsługiwane klucze virtual_params w silniku:
      bm25_k1, bm25_b, synonym_weight, confidence_threshold
    """
    vp: dict[str, Any] = {}
    for key, val in flat_combo.items():
        if key == "bm25.k1":
            vp["bm25_k1"] = val
        elif key == "bm25.b":
            vp["bm25_b"] = val
        elif key == "bm25.synonimy_waga":
            vp["synonym_weight"] = val
        # confidence_threshold – nie przekazujemy do virtual_params silnika;
        # lab używa go osobno jako próg odcięcia przy accuracy
    return vp


def _evaluate_config(
    wyszukiwarka: Any,
    questions: list[tuple[str, str, str]],
    flat_combo: dict[str, Any],
) -> dict[str, Any]:
    """
    Ocenia jedną konfigurację:
    - wywołuje wyszukiwarka.szukaj dla każdej pary (pytanie, oczekiwany)
    - liczy accuracy  = odsetek trafień w właściwy paragraf  ← główna metryka
    - liczy avg_confidence = średnie podobieństwo top-1       ← pomocnicza
    - liczy min_confidence = minimum podobieństwa (0 gdy brak wyników)
    """
    vp = _build_virtual_params(flat_combo)
    total_conf = 0.0
    min_conf = 1.0
    hits_confidence = 0  # wyniki z conf > 0
    hits_accuracy = 0  # trafienia w właściwy paragraf

    has_expected = any(oczekiwany for _, oczekiwany, _ in questions)

    for pytanie, oczekiwany, ocz_punkt in questions:
        wyniki = wyszukiwarka.szukaj(
            pytanie, n_wynikow=1, virtual_params=vp if vp else None
        )
        if wyniki:
            conf = wyniki[0].podobienstwo
            total_conf += conf
            min_conf = min(min_conf, conf)
            if conf > 0:
                hits_confidence += 1

            tytul = wyniki[0].tytul
            tresc = wyniki[0].tresc

            sukces = False
            if oczekiwany and oczekiwany.lower() in tytul.lower():
                sukces = True

            if sukces and ocz_punkt:
                sukces = ocz_punkt.lower() in tresc.lower()

            if sukces:
                hits_accuracy += 1
        else:
            # Brak wyników → conf = 0, min_conf nie rośnie
            min_conf = min(min_conf, 0.0)

    n = max(len(questions), 1)
    n_with_expected = max(sum(1 for _, o, _ in questions if o), 1)

    return {
        "accuracy": round(hits_accuracy / n_with_expected, 4) if has_expected else None,
        "avg_confidence": round(total_conf / n, 4),
        "min_confidence": round(min_conf, 4) if min_conf < 1.0 else 0.0,
        "hits": hits_confidence,
    }


# ── 5. Główna funkcja grid-search ────────────────────────────────────────────


def run_grid_search(
    questions_path: str | None = None,
    max_combinations: int = DOMYSLNA_LICZBA_KOMBINACJI,
    sekcje: list[str] | None = None,
) -> dict[str, Any]:
    """
    1. Wczytuje pytania z data/config/testy.toml (lub podanego pliku).
    2. Buduje wyszukiwarkę (jednorazowo).
    3. Generuje siatkę parametrów liczbowych z config.toml.
    4. Losowo ogranicza do max_combinations (lazy – bez ładowania całości do RAM).
    5. Ocenia każdą kombinację → wybiera najlepszą wg accuracy (gdy dostępna)
       lub avg_confidence (gdy brak info o oczekiwanych paragrafach).
    6. Zapisuje wynik do data/config/optimal_config.json.
    7. Zwraca słownik z wynikami.
    """
    print("=== Lab Simulation – Grid Search ===")

    # --- pytania ---
    questions = load_questions(questions_path, sekcje=sekcje)
    has_expected = any(oczekiwany for _, oczekiwany, _ in questions)
    print(f"Pytań do testowania: {len(questions)}")
    print(
        f"Metryka główna: {'accuracy (trafność paragrafu)' if has_expected else 'avg_confidence'}"
    )

    # --- wyszukiwarka (raz) ---
    from infrastructure.knowledge_loader import utworz_wyszukiwarke

    base_dir = pathlib.Path(__file__).resolve().parents[1]
    data_dir = base_dir / "data"
    wyszukiwarka = utworz_wyszukiwarke(str(data_dir))

    # --- parametry ---
    base_cfg = load_base_config()
    flat_cfg = _flatten_numeric(base_cfg)
    print(f"Parametrów do optymalizacji: {len(flat_cfg)}")
    for k, v in flat_cfg.items():
        print(f"  {k} = {v}")

    total_combos = _count_combinations(flat_cfg)
    print(f"Wszystkich kombinacji: {total_combos}")

    # Lazy sampling: jeśli za dużo – losujemy indeksy, nie ładujemy wszystkiego
    if total_combos > max_combinations:
        random.seed(42)  # nosec B311

        # 1. Zbieramy możliwe opcje dla każdego parametru
        param_options = {}
        for key, val in flat_cfg.items():
            if isinstance(val, int):
                step = max(1, abs(val) // 5)
                param_options[key] = sorted({val - step, val, val + step})
            elif isinstance(val, float):
                step = max(0.05, abs(val) * 0.2)
                param_options[key] = sorted(
                    {round(val - step, 3), round(val, 3), round(val + step, 3)}
                )

        # 2. Losujemy kombinacje bezpośrednio (O(N) względem max_combinations, a nie total_combos)
        combos = []
        for _ in range(max_combinations):
            combo = {k: random.choice(opts) for k, opts in param_options.items()}  # nosec B311
            combos.append(combo)

        print(f"Losowo wygenerowano {max_combinations} kombinacji")
    else:
        combos = list(_generate_param_grid(flat_cfg))

    # --- przeszukiwanie ---
    best_score = -1.0
    best_combo: dict[str, Any] = {}
    best_metrics: dict[str, Any] = {}
    results_log: list[dict[str, Any]] = []

    for idx, combo in enumerate(combos):
        metrics = _evaluate_config(wyszukiwarka, questions, combo)

        # Główna metryka: accuracy jeśli dostępna, inaczej avg_confidence
        score = (
            metrics["accuracy"]
            if (has_expected and metrics["accuracy"] is not None)
            else metrics["avg_confidence"]
        )

        results_log.append(
            {
                "index": idx,
                "params": combo,
                "metrics": metrics,
            }
        )

        if score > best_score:
            best_score = score
            best_combo = combo
            best_metrics = metrics

        # Progres co 10 kombinacji
        if (idx + 1) % 10 == 0 or idx == len(combos) - 1:
            metric_label = "accuracy" if has_expected else "avg_conf"
            print(f"  [{idx + 1}/{len(combos)}] best_{metric_label}={best_score:.4f}")

    # --- zapis optymalnej konfiguracji ---
    optimal_path = base_dir / "data" / "config" / "optimal" / "optimal_config.json"
    optimal_path.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "best_config": best_combo,
        "metrics": best_metrics,
        "questions_used": len(questions),
        "combinations_tested": len(combos),
        "metric": "accuracy" if has_expected else "avg_confidence",
    }
    with optimal_path.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nOptymalna konfiguracja zapisana do: {optimal_path}")

    return output


# ── 6. Uruchomienie standalone ────────────────────────────────────────────────


if __name__ == "__main__":
    from core.bd import inicjalizuj

    inicjalizuj()
    result = run_grid_search()
    print("\n=== WYNIK ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))
