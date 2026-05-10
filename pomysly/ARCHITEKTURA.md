# Architektura i Standardy Kodowania (Asystent PWr v2)

Ten dokument definiuje docelową architekturę techniczną i standardy inżynierskie projektu. Znajdują się tu wyłącznie zadania, które nie dodają nowych funkcji dla użytkownika (features), ale dbają o to, by kod był czysty, profesjonalny i zgodny z regułami **Domain-Driven Design (DDD)** oraz **Clean Architecture**.

## Legenda statusów
- `DONE` — zasada/wzorzec wdrożony
- `PARTIAL` — zasada/wzorzec wdrożona częściowo lub z ograniczeniami
- `TODO` — zasada/wzorzec zaplanowany do wdrożenia

---

## 1. Architektura i Wzorce Projektowe

### 1.1 Refaktoryzacja na Serwisy Aplikacyjne (Clean Architecture)
- `DONE` Separacja logiki biznesowej od routera (Flaska). Cała logika znajduje się w `v2/domain/services/`. Plik `app.py` pełni wyłącznie rolę punktu wejściowego (API).

### 1.2 Wzorzec Repozytorium (Repository Pattern)
- `DONE` Przeniesienie zapytań SQL z `core/bd.py` do dedykowanych klas repozytoriów.
- **Wdrożone Repozytoria:** `PytaniaRepository`, `FeedbackRepository` w `v2/domain/repositories/`. Plik `bd.py` pełni rolę cienkiej warstwy delegującej (thin wrapper).

### 1.3 Obiekty Dziedzinowe (Value Objects / Dataclasses)
- `DONE` Zastąpienie przestarzałych słowników (`dict`) ścisłymi typami strukturalnymi używając `@dataclass`.
- **Wdrożone Obiekty:** `WynikWyszukiwania`, `Paragraf`, `OdpowiedzAPI` w pliku `v2/domain/models.py`.

### 1.4 Separacja Warstwy Infrastruktury
- `DONE` Utworzenie dedykowanego folderu `v2/infrastructure/`.
- **Wdrożone Komponenty:** Parser PDF (`pdf_parser.py`), obsługa cache (`knowledge_loader.py`). Katalog `core/` jest wolny od logiki wejścia/wyjścia (I/O).

- `DONE` Usunięcie globalnych instancji w plikach (np. `wyszukiwarka` w `app.py`) na rzecz wzorca DI. Przekazywanie obiektów do serwisów za pomocą kontenera (klasa `Container`).

---

## 2. Optymalizacja i Czystość Kodu

### 2.1 Asynchroniczne logowanie statystyk
- `DONE` Wykorzystanie modułu `threading` do zapisu feedbacku i logów "do poprawy" w tle. Dzięki temu API nie czeka na operacje I/O dysku przed wysłaniem potwierdzenia do klienta.

### 2.2 Standaryzacja Importów (PEP 8 Policy)
- `DONE` Uporządkowanie importów (biblioteki wbudowane -> zewnętrzne -> lokalne absolutne). Eliminacja importów względnych w całym projekcie.

### 2.3 Ścisłe Typowanie (Strict Type Hinting)
- `DONE` Wymuszenie adnotacji typów (PEP 484) dla wszystkich metod i funkcji w całym projekcie.
- **Wdrożone Zmiany:** Pełne typowanie w `core/`, `infrastructure/`, `domain/` oraz `app.py`. Projekt wykorzystuje `TYPE_CHECKING` do optymalizacji importów i jest przygotowany pod statyczną analizę `mypy`.

---

## 3. Pipeline CI/CD (GitHub Actions)

Obecnie skrypt weryfikuje składnię (`ruff`) oraz odpala plik `test.py`. To nie jest wystarczające, ponieważ `test.py` zawsze zwraca status `0` (sukces), niezależnie od tego czy zdało 10, czy 150 testów.

### 3.1 Testowanie Regresji (Zabezpieczenie Wyników)
- `DONE` Zmiana wywoływanego skryptu z `tests/test.py` na `tests/test_diff.py` w pliku `.github/workflows/testy.yml`. Skrypt `test_diff.py` automatycznie zatrzyma wdrożenie i zwróci błąd (`exit code 1`), jeśli wprowadzona przez Ciebie zmiana pogorszy algorytm poniżej obecnego Baseline (103/150).

### 3.2 Diagnostyka i Observability (Admin View)
- `TODO` Wprowadzenie wzorca "Health Check" dla infrastruktury.
- **Zasada:** System musi udostępniać endpoint diagnostyczny (zabezpieczony tokenem), który weryfikuje integralność bazy wiedzy (JSON), połączenie z bazą SQL oraz status cache'owania w locie. Umożliwi to szybką identyfikację problemów po stronie hostingu (np. Render/Heroku).

### 3.3 Weryfikacja Typów (Mypy) w CI
- `DONE` Zintegrowanie narzędzia `mypy` w potoku GitHub Actions w celu sprawdzania zgodności typów przy każdym Commicie.

### 3.4 Walidacja Formatowania Kodu
- `DONE` Rozszerzenie potoku GitHub Actions o sprawdzenie formatowania (np. `ruff format --check`).

---

> Dokument jest systematycznie aktualizowany po każdej znaczącej reorganizacji kodu i struktury plików.
