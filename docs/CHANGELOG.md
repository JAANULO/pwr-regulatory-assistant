# 📝 Dziennik Zmian (CHANGELOG) — Asystent PWr v2

Wszystkie istotne zmiany w projekcie są odnotowywane w tym pliku zgodnie ze standardem [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [2.5.0] - 2026-05-17
### Dodano
- **Karty Szybkiej Odpowiedzi (Słownik pojęć - 2.3)**: Wdrożenie mechanizmu natychmiastowego serwowania oficjalnych definicji z § 2 regulaminu studiów PWr (np. absolwent, student, punkty ECTS) w 100% poprawnej polszczyźnie (bez mojibake).
- **Dwuetapowe dopasowywanie intencji**: Zaprojektowanie bezpiecznego dopasowania fraz wielowyrazowych oraz precyzyjnego oczyszczania podmiotu dla wyrazów jednowyrazowych, co unika fałszywych dopasowań (np. powtarzanie przedmiotu).
- **Integracja bezinwazyjna**: Wpięcie szybkiej ścieżki w `Wyszukiwarka.szukaj()` oraz `execute_ask_question()` bez konieczności jakichkolwiek modyfikacji w kodzie frontendu (pełna kompatybilność wsteczna).
- **Laboratorium Regulaminowe (Tryb Symulacji - symulacja.md)**: Wdrożenie pełnego wsparcia dla specyfikacji trybu symulacji: zaimplementowano dynamiczny próg pewności (`confidence_threshold` / "Nie wiem"), zintegrowano nowy suwak we frontendzie, zaimplementowano parametryzację CLI w skrypcie `tests/test.py` do masowych symulacji z konsoli, oraz przywrócono pełną wierność symulacji systemu (usunięto sztuczny bypass szybkich ścieżek).
- **Testy**: Dodanie przypadków weryfikacyjnych dla pojęć słownikowych do `tests/test.py`. Skuteczność testów regresyjnych wynosi **110/156** zaliczonych przypadków.
- **Wyszukiwarka (Korekcja Fonetyczna - 2.4)**: Wdrożenie uproszczeń fonetycznych języka polskiego (Homophonic Polish Fuzzy Search). Słowa zawierające wyłącznie błędy ortograficzne (np. `rezignacja`, `gurny`, `hrobry`) są korygowane w czasie O(1).
- **Potok NLP**: Przebudowanie kolejności tokenizacji (Stopwords -> Korekcja literówek -> Synonimy), co odblokowało korekcję literówek na synonimach i studenckim slangu (np. `dzekansky` -> `dziekański`).
- **Skrypt Walidacyjny (3.4)**: Utworzenie `tests/validate_dictionaries.py` w celu wykrywania cykli, błędów składni, nieoczyszczonych kluczy i łańcuchów normalizacji w bazie słowników.
- **Integracja CI/CD**: Dodanie automatycznego testu spójności słowników TOML do potoku GitHub Actions (`testy.yml`).
- **Testy**: Rozszerzenie bazy testowej `tests/test.py` o trudne pytania fonetyczne w `TESTY_TRUDNE`.

### Naprawiono
- **Słowniki (UTF-8 i Mojibake)**: Przekonwertowanie `synonimy.toml` i `rozszerzenia.toml` z formatu CP1250 na poprawny UTF-8. Usunięto cichą korupcję polskich znaków (mojibake) i przywrócono działanie martwym dotąd kluczom (np. `"dyplom ukonczenia"`, `"srednia wazona"`), co podniosło celność wyszukiwarki do **108/153** testów.
- **Normalizacja (Usunięcie konfliktu)**: Wyeliminowanie błędnego mapowania `"punkty" = "ocena"`, które tworzyło cykle i konflikty logiczne.

---

## [2.3.0] - 2026-05-10
### Dodano
- **Struktura (Root Migration & Cleanup)**: Pełne przeniesienie projektu do roota. Reorganizacja plików pomocniczych do folderów `/docs` (dokumentacja), `/docs/research` (notatki) oraz `/deployment` (Docker/Gunicorn).
- **Optymalizacja Wyszukiwarki**: Przeniesienie `STOPWORDS` poza funkcję `tokenizuj` (znaczny wzrost wydajności przy seryjnych zapytaniach).
- **Poprawa Skuteczności**: Rozszerzenie słowników o frazy dotyczące praktyk zawodowych i ECTS. Wynik testów regresji wzrósł do **65.7%** (+3 punkty).
- **Czyszczenie Kodu**: Usunięcie martwego kodu oraz unifikacja stałej `ROOT_DIR`.
- **Automatyzacja**: Wdrożenie `pre-commit` z linterem `ruff` i autotestem weryfikacyjnym.

### Naprawiono
- **Błędy JS**: Naprawa literówki w wyborze źródła wiedzy oraz przywrócenie poprawnego działania historii zapytań.
- **Słowniki**: Poprawa krytycznych literówek w kluczach `egzamin` i `kolokwium`.
- **Regex**: Naprawa błędów w podziale zdań (obsługa skrótów `m.in.`, `poz.`).

---

## [2.2.0] - 2026-05-10
### Dodano
- **Wzorce Projektowe**: Wdrożenie kontenera zależności (**Dependency Injection**) poprzez klasę `Container`. Usunięto globalne instancje z `app.py`.
- **Wydajność**: Asynchroniczne zapisywanie feedbacku i logów przy użyciu modułu `threading` (non-blocking I/O).
- **Infrastruktura**: Nowy plik `infrastructure/container.py` zarządzający cyklem życia komponentów.

### Naprawiono
- **CI/CD**: Usunięcie nieużywanych importów (`logging`, `LOG_LEVEL`) oraz naprawa formatowania w plikach `app.py` i `container.py`.
- **Stabilność**: Naprawa uszkodzonych importów w `app.py` po refaktoryzacji.

---

## [2.1.0] - 2026-05-09
### Dodano
- **Ścisłe Typowanie (PEP 484)**: Pełne adnotacje typów w całym projekcie, przygotowanie pod analizę `mypy`.
- **Regression Testing**: Wdrożenie `tests/test_diff.py` porównującego wyniki z `baseline.json`. Automatyczna blokada wdrożeń pogarszających jakość (Baseline: 103/150).

### Zmieniono
- **Architektura (Clean Architecture)**: Wyodrębnienie logiki biznesowej do `domain/services/` oraz repozytoriów do `domain/repositories/`.
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
