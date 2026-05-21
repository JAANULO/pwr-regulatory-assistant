# Architektura i Standardy Kodowania (Asystent PWr v2)

Ten dokument definiuje docelową architekturę techniczną i standardy inżynierskie projektu. Znajdują się tu wyłącznie zadania, które nie dodają nowych funkcji dla użytkownika (features), ale dbają o to, by kod był czysty, profesjonalny i zgodny z regułami **Domain-Driven Design (DDD)** oraz **Clean Architecture**.

## Legenda statusów
- `DONE` — zasada/wzorzec wdrożony
- `PARTIAL` — zasada/wzorzec wdrożona częściowo lub z ograniczeniami
- `TODO` — zasada/wzorzec zaplanowany do wdrożenia

---

## 1. Architektura i Wzorce Projektowe

### 1.1 Refaktoryzacja na Serwisy Aplikacyjne (Clean Architecture)
- `DONE` Separacja logiki biznesowej od routera (Flaska). Cała logika znajduje się w `domain/services/`. Plik `app.py` pełni wyłącznie rolę punktu wejściowego (API).

### 1.2 Wzorzec Repozytorium (Repository Pattern)
- `DONE` Przeniesienie zapytań SQL z `core/bd.py` do dedykowanych klas repozytoriów.
- **Wdrożone Repozytoria:** `PytaniaRepository`, `FeedbackRepository` w `domain/repositories/`. Plik `bd.py` pełni rolę cienkiej warstwy delegującej (thin wrapper).

### 1.3 Obiekty Dziedzinowe (Value Objects / Dataclasses)
- `DONE` Zastąpienie przestarzałych słowników (`dict`) ścisłymi typami strukturalnymi używając `@dataclass`.
- **Wdrożone Obiekty:** `WynikWyszukiwania`, `Paragraf`, `OdpowiedzAPI` w pliku `domain/models.py`.

### 1.4 Separacja Warstwy Infrastruktury
- `DONE` Utworzenie dedykowanego folderu `infrastructure/`.
- **Wdrożone Komponenty:** Parser PDF (`pdf_parser.py`), obsługa cache (`knowledge_loader.py`). Katalog `core/` jest wolny od logiki wejścia/wyjścia (I/O).

- `DONE` Usunięcie globalnych instancji w plikach (np. `wyszukiwarka` w `app.py`) na rzecz wzorca DI. Przekazywanie obiektów do serwisów za pomocą kontenera (klasa `Container`).

### 1.5 Separacja danych słownikowych od logiki (Data vs Code)
- `DONE` Przeniesienie twardo zakodowanych słowników (`SYNONIMY`, `ROZSZERZENIA`) z `core/slowniki.py` do zewnętrznych plików konfiguracyjnych TOML ładowanych przez warstwę infrastruktury przy użyciu natywnego parsera `tomllib`.
- **Korzyść:** Kod `core/` staje się całkowicie deklaratywny i wolny od surowych danych, spełniając zasady Clean Architecture.

### 1.6 Pełna eliminacja proceduralnego wrappera bazy danych (`core/bd.py`)
- `TODO` Całkowite zastąpienie odwołań do funkcji proceduralnych w `core/bd.py` bezpośrednimi wywołaniami do repozytoriów wstrzykiwanych przez Kontener DI.
- **Korzyść:** Ujednolicenie architektury bazodanowej zgodnie z DDD. Serwisy aplikacyjne i routery będą korzystać wyłącznie z wstrzykiwanych instancji `PytaniaRepository` oraz `FeedbackRepository` z `domain/repositories/`, eliminując przestarzałą warstwę proceduralnego wrappera.

### 1.7 Separacja parametrów wyszukiwania (Konfiguracja hiperparametrów)
- `DONE` Wyodrębnienie wszystkich parametrów wyszukiwania (stałe BM25 `k1` i `b`, siła synonimów, mapy wag statycznych i dynamicznych oraz boosting słów) do zewnętrznego pliku `data/config/config.toml`.
- **Implementacja:** Stworzono system dynamicznego wczytywania `data/config/config.toml` przy użyciu wbudowanej biblioteki `tomllib`. Silnik wyszukiwarki automatycznie wykrywa zmiany w pliku TOML (za pomocą sprawdzania czasu modyfikacji pliku `mtime` bez konieczności restartu aplikacji), co pozwala na natychmiastowe strojenie hiperparametrów w locie, w tym z poziomu panelu laboratoryjnego.

- **Zasada podziału parametrów (Standard Architektoniczny):**
  1. **Hiperparametry algorytmiczne (`data/config/config.toml`):** Stałe BM25 (`k1`, `b`), waga synonimów, podbicie pojęć (`term_boosts`), wagi statyczne i dynamiczne rozdziałów. Podlegają dynamicznemu strojeniu (*hot-reload*). Do tej grupy zaliczają się również progi NLP (jak `PROG_DLUGOSCI_SLOWA_KOREKCJA`, współczynnik agregacji pytań wielozdaniowych, czy progi dopasowania słownika), które powinny docelowo trafić do tego pliku.
  2. **Infrastruktura i konfiguracja uruchomieniowa (`.env` / `core/settings.py`):** Timeouty połączeń DB, tryby SSL, porty sieciowe, adresy hostów i klucze API. Te zmienne zależą od środowiska (dev/prod) i **nie są wersjonowane w Git** ze względów bezpieczeństwa.
  3. **Wewnętrzne stałe implementacyjne (Kod źródłowy):** Np. zakresy długości w Regex w `core/intencje.py`. Są to sztywne reguły kodu, których modyfikacja przez użytkownika mogłaby uszkodzić stabilność parsera.

### 1.8 Separacja struktur danych języka naturalnego
- `DONE` Wydzielenie twardo zakodowanych struktur danych języka naturalnego (słowników tematów, intencji, fraz pomocniczych, powitań z emoji oraz losowych zachęt) z modułów w katalogu `core/` do zewnętrznych plików konfiguracyjnych TOML w katalogu `data/config/`.
- **Implementacja:** Utworzono pliki konfiguracyjne TOML: `data/config/szybkie_odpowiedzi.toml`, `data/config/intencje.toml`, `data/config/formatowanie.toml`. Zaimplementowano dynamiczne wczytywanie w locie (*hot-reload*) oparte na śledzeniu czasu modyfikacji (`mtime`) z zachowaniem pełnej odporności na błędy (fallbacki bezpośrednio w kodzie).

### 1.9 Architektura Wielomodelowa w QA (Multi-LLM Testing)
- `TODO` Przygotowanie platformy testów automatycznych pod obsługę wielu dostawców AI (Gemini, OpenAI ChatGPT, DeepSeek) w zaawansowanym trybie oceny krzyżowej (*Multi-Agent Cross-Evaluation*) z ochroną limitów API oraz pełną kontrolą deweloperską.
- **Planowana Implementacja:**
  1. **Zróżnicowane Generowanie Pytania (Diverse Test Generation):** Każdy z modeli (Gemini, ChatGPT, DeepSeek) na podstawie bazy wiedzy generuje unikalną podgrupę pytań (o różnym stylu i stopniu potoczności), które łączone są w jeden wspólny, zróżnicowany zestaw testowy (*Diverse Test Suite*).
  2. **Wielomodelowa Ocena Krzyżowa (Consensus Cross-Evaluation):** Każda odpowiedź wygenerowana przez wyszukiwarkę programu jest niezależnie weryfikowana przez wszystkie wybrane modele LLM (każde pytanie oceniane przez każdy z modeli).
  3. **Optymalizacja Kosztów Tokenów (Hybrid Judge-Architect Architecture):** 
     * **Tani Sędziowie Binarni (Binary Judges):** Do weryfikacji pytań (Krok 2) modele (np. GPT-4o-mini, Gemini-Flash) są odpytywane wyłącznie o prosty, tani status binarny (`{"trafny": true/false}`). Ogranicza to liczbę tokenów wyjściowych do minimum.
     * **Lokalny Konsensus:** Skrypt Pythona zlicza głosy (np. 2:1 na nie) bez udziału AI.
     * **Jeden Zbiorczy Architekt (Master QA):** Dopiero po zakończeniu wszystkich testów, lista potwierdzonych błędów jest wysyłana w **jednym, zbiorczym zapytaniu** do jednego wybranego, najbardziej analitycznego modelu (np. DeepSeek-R1 lub Gemini-Flash), który analizuje całość i generuje sugerowane poprawki. Oszczędza to do 90% tokenów.
  4. **Wzorzec Adapter (Adapter Pattern):** Klasy `GeminiClient`, `OpenAIClient`, `DeepSeekClient` dziedziczące po abstrakcyjnym `BaseLLMClient` w celu unifikacji odpytywania API.
  5. **Zarządzanie Limitami API i Buforowanie Czasu (Smart Rate Limiting):** Wprowadzenie inteligentnego kolejkowania żądań z dynamicznymi opóźnieniami czasowymi (*interval buffering*), wykrywaniem błędów `HTTP 429` oraz automatycznym ponawianiem według wykładniczego czasu oczekiwania (*exponential backoff*). Zapobiega to wyczerpaniu darmowych tokenów i zablokowaniu kont.
  6. **Kontrola Deweloperska (Human-in-the-Loop / Log-Only Strategy):** Wyłączenie automatycznej modyfikacji kodu słowników. Wszystkie oceny sędziów AI, komentarze oraz wyliczony konsensus są zapisywane wyłącznie do logów (`logs/auto_test_wyniki.json` oraz `logs/auto_test_poprawki.py`), a ostateczną decyzję o wdrożeniu poprawek podejmuje deweloper po ręcznej weryfikacji.
  7. **Zarządzanie sekretami i modelami:** Dodanie kluczy `OPENAI_API_KEY`, `DEEPSEEK_API_KEY` do pliku `.env` oraz zmiennej `LLM_PROVIDER_SUITE` określającej aktywne modele oceniające.

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
- `DONE` Wprowadzenie wzorca "Health Check" dla infrastruktury.
- **Zasada:** System udostępnia endpoint `/admin/health` (zabezpieczony tokenem), który weryfikuje integralność bazy wiedzy (JSON), połączenie z bazą SQL oraz status cache'owania w locie. Umożliwia to szybką identyfikację problemów po stronie hostingu.

### 3.3 Weryfikacja Typów (Mypy) w CI
- `DONE` Zintegrowanie narzędzia `mypy` w potoku GitHub Actions w celu sprawdzania zgodności typów przy każdym Commicie.

### 3.4 Walidacja Formatowania Kodu
- `DONE` Rozszerzenie potoku GitHub Actions o sprawdzenie formatowania (np. `ruff format --check`).

---

> Dokument jest systematycznie aktualizowany po każdej znaczącej reorganizacji kodu i struktury plików.
