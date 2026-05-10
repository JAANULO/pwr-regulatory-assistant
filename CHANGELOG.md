# 📝 Dziennik Zmian (CHANGELOG) — Asystent PWr v2

Wszystkie istotne zmiany w projekcie są odnotowywane w tym pliku zgodnie ze standardem [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [2.2.0] - 2026-05-10
### Dodano
- **Wzorce Projektowe**: Wdrożenie kontenera zależności (**Dependency Injection**) poprzez klasę `Container`. Usunięto globalne instancje z `app.py`.
- **Wydajność**: Asynchroniczne zapisywanie feedbacku i logów przy użyciu modułu `threading` (non-blocking I/O).
- **Infrastruktura**: Nowy plik `v2/infrastructure/container.py` zarządzający cyklem życia komponentów.

### Naprawiono
- **CI/CD**: Usunięcie nieużywanych importów (`logging`, `LOG_LEVEL`) oraz naprawa formatowania w plikach `app.py` i `container.py`.
- **Stabilność**: Naprawa uszkodzonych importów w `v2/app.py` po refaktoryzacji.

---

## [2.1.0] - 2026-05-09
### Dodano
- **Ścisłe Typowanie (PEP 484)**: Pełne adnotacje typów w całym projekcie, przygotowanie pod analizę `mypy`.
- **Regression Testing**: Wdrożenie `tests/test_diff.py` porównującego wyniki z `baseline.json`. Automatyczna blokada wdrożeń pogarszających jakość (Baseline: 103/150).

### Zmieniono
- **Architektura (Clean Architecture)**: Wyodrębnienie logiki biznesowej do `v2/domain/services/` oraz repozytoriów do `v2/domain/repositories/`.
- **UI/UX**: Przywrócenie oryginalnego, ciemnego motywu ("neonowego") po odrzuceniu wersji hybrydowej.

---

## [2.0.0] - 2026-04-16
### Dodano
- **Multi-Baza**: Obsługa wielu plików JSON jako źródeł wiedzy. Endpoint `/zapytaj` przyjmuje parametr `zrodlo`.
- **Graf Relacji**: Nowa metoda `generuj_graf_paragrafow()` wykorzystująca podobieństwo kosinusowe TF-IDF.
- **Frontend**: Dropdown wyboru bazy oraz podświetlanie (highlight) słów kluczowych w tekście.
- **Testy**: Rozbudowa bazy testowej do 150 przypadków. Nowy skrypt `tests/weryfikacja.py`.

### Zmieniono
- **Algorytm**: Powrót do standardowego wektoryzatora po wycofaniu Odwróconego Indeksu.

---

## [1.1.0] - 2026-04-07
### Dodano
- **Diagnostyka**: System Render Debug (`/admin/debug`) oraz Authenticated Traceback dla administratora.
- **Optymalizacja**: Usunięcie ciężkich zależności (PyTorch) z wersji produkcyjnej, co przyspieszyło deployment.
- **UX**: Dodano indykator "Szukam informacji..." (Thinking State).

---

## [1.0.0] - 2026-03-30
### Dodano
- **Silnik BM25**: Pierwsza stabilna wersja asystenta oparta na modelu przestrzeni wektorowej.
- **Dashboard Admina**: Statystyki, eksport CSV oraz zarządzanie synonimami "na żywo".
- **UX**: Historia sesji w `localStorage`, motyw jasny/ciemny oraz eksport do PDF.
- **Bezpieczeństwo**: Automatyczne logowanie słabych odpowiedzi do `logs/do_poprawy.txt`.
