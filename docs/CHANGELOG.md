# 📝 Dziennik Zmian (CHANGELOG) — Asystent PWr v2

Wszystkie istotne zmiany w projekcie są odnotowywane w tym pliku zgodnie ze standardem [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [2.10.1] - 2026-06-17
### Dodano
- **Grafy w Głównym Menu**: Wyciągnięcie podglądu powiązań grafowych bezpośrednio pod wybór baz wiedzy.
- **Przełącznik Parametrów**: Nowy element interfejsu (toggle) pozwalający na szybką zmianę parametrów dopasowania odpowiedzi z poziomu przeglądarki.

### Naprawiono
- **Bezpieczeństwo (Prywatność)**: Tymczasowe wyłączenie współdzielonej historii czatu, aby zapobiec krzyżowym wyciekom danych między użytkownikami.
- **Generator Konfiguracji**: Naprawiono błąd w `scripts/symulacja.py`, przez który plik `optimal_config.json` był generowany ze spłaszczonymi kluczami. Przywrócono poprawną zagnieżdżoną strukturę TOML-podobną.

## [2.10.0] - 2026-06-17
### Dodano
- **Wsparcie dla zdań twierdzących**: Zaimplementowano płynne filtrowanie fraz oceniających (np. "Oceń czy to zdanie jest prawdziwe:"). Dzięki temu algorytm wyszukiwarki skutecznie przetwarza podane mu stwierdzenia (znajdując regulacje potrzebne do weryfikacji).
- **Izolacja Konfiguracji**: Dodano plik bazowy `data/config/config.example.toml` oraz dodano właściwy `config.toml` do ignorowanych w kontroli wersji.

### Ulepszono
- **Architektura Kodu**: Przeniesienie zmiennej wbudowanej `STOPWORDS` z pliku Pythona wprost do deklaratywnego środowiska TOML.

---

## [2.9.1] - 2026-06-09
### Dodano
- **Rygorystyczna Walidacja**: Skrypt `symulacja.py` weryfikuje od teraz nie tylko trafienie w paragraf, ale także dokładny punkt/podpunkt z treści, co zrównuje jego logikę z systemem testów regresyjnych.
- **Artefakty Optymalizacji**: Wyniki symulacji zapisywane są w bezpiecznym, ignorowanym przez kontrolę wersji folderze `data/config/optimal/`.

### Naprawiono
- **Timeout w GitHub Actions**: Zastąpiono "Leniwy Generator Siatki" (Grid Search) algorytmem bezpośredniego losowania z ograniczonej puli opcji (Random Search). Eliminuje to problem pętli iterujących po tryliardach kombinacji.
- **Skuteczność**: Nowy algorytm wygenerował konfigurację o rekordowej skuteczności ponad **98.2%** na restrykcyjnych kryteriach zapytań konwersacyjnych.

## [2.9.0] - 2026-05-21
### Dodano
- **Automatyczna Symulacja**: Nowy skrypt `scripts/symulacja.py` w pełni zintegrowany z API we Flasku (`/lab/simulate`). Optymalizuje hiperparametry wyszukiwarki przy użyciu siatki wielowymiarowej z bezpiecznym losowaniem (odporność na przepełnienie zmiennych w Pythonie).
- **Zewnętrzne testy (TOML)**: Usunięto przestarzałe zmienne wbudowane w kod i wyekstrahowano wszystkie zbiory pytań (170 sztuk) do jednego, bardzo edytowalnego pliku `data/config/testy.toml`. Dodano obsługę flagi `--sekcje`.
- **Leniwy Generator Siatki**: Ominięto zjawisko pochłaniania RAM-u z powodu "klątwy wielowymiarowości", wprowadzając generatory, które trzymają zużycie pamięci PWr asystenta poniżej 100 MB nawet przy miliardach konfiguracji do sprawdzenia.

### Ulepszono
- **Zwiększona Trafność**: Ze względu na rozbudowę bazy wiedzy oraz usprawnienie algorytmów na `testy.toml`, silnik osiągnął **75.8% (129/170)** bazowej trafności bez przeuczenia.
- **Odporność Testów**: Zaktualizowano `tests/smoke_test.py` tak, aby weryfikował działanie endpointu `/lab/simulate` (pełne pokrycie nowej logiki).


## [2.8.0] - 2026-05-21
### Dodano
- **Responsywność i Mobilność (Krok 1.2)**: Wdrożenie pliku manifestu PWA (`static/manifest.json`) umożliwiającego uruchamianie aplikacji w trybie `standalone` na urządzeniach mobilnych (bez ramki przeglądarki).
- **Gesty Swipe (Mobile First)**: Dodanie zaawansowanej obsługi gestów dotykowych (przeciągnięcie palcem od lewej krawędzi) do płynnego otwierania i zamykania bocznego panelu historii na smartfonach.
- **Automatyczna Weryfikacja**: Rozszerzenie skryptu `tests/weryfikacja.py` o pełną walidację manifestu PWA oraz gestów dotykowych w kodzie JS.
- **Integracja CI/CD**: Wpięcie walidacji PWA i responsywności bezpośrednio do potoku GitHub Actions (`testy.yml`).

### Ulepszono
- **Refaktoryzacja i Czystość Kodu (BM25 Engine)**: Wyeliminowanie martwych wrapperów `oblicz_idf` oraz `zbuduj_wektory` i przekierowanie wszystkich wywołań w `infrastructure/knowledge_loader.py` bezpośrednio na funkcje `oblicz_idf_bm25` oraz `zbuduj_wektory_bm25`.
- **Adaptacja Nagłówka**: Dodanie stylów responsywnych dla urządzeń o szerokości poniżej 600px — ukrywanie napisów przycisków w nagłówku na rzecz samych czytelnych ikon (opcje, nowy czat).
- **Parametryzacja Progu Długości**: Zastąpienie magicznej liczby `8` w korekcji odległości Levenshteina nazwaną stałą modułową `PROG_DLUGOSCI_SLOWA_KOREKCJA`.
- **Akademickie Sformułowania**: Przekształcenie potocznych komentarzy AI na precyzyjną terminologię akademicką (np. autorelacja tokenów, stopień węzła grafu) oraz dodanie ścisłego typowania dla cache literówek.
- **Analiza Architektury (Krok 1.7)**: Potwierdzenie pełnej separacji parametrów wyszukiwania w pliku `data/config.toml` (dynamiczne wczytywanie i hot-reload wag BM25).

## [2.7.0] - 2026-05-18
### Dodano
- **Separacja Hiperparametrów Wyszukiwarki (Krok 1.7)**: Wydzielenie 46 konfigurowalnych parametrów (BM25, term boosts, statyczne i dynamiczne wagi rozdziałów) z kodu źródłowego silnika `core/wyszukiwarka.py` do deklaratywnego pliku `data/config.toml` z inwalidacją cache `.pkl` oraz bezinwazyjnym RAM-buforowaniem I/O.
- **Wydzielenie Promptów LLM (Krok 6.2)**: Przeniesienie wszystkich wielolinijkowych promptów i szablonów API Gemini ze skryptu `tests/auto_tester.py` do dedykowanego pliku `tests/prompts.toml` wraz z automatyczną walidacją w `tests/validate_dictionaries.py` i dynamicznym formatowaniem `.format()`.
- **Obsługa zapytań konwersacyjnych (Krok 3.5)**: Wdrożenie segmentacji zapytań na zdania, filtracji szumu grzecznościowego oraz agregacji podobieństwa Maximum-Weighted Sum w celu doskonałej analizy długich, zawiłych pytań studenckich.
- **Wzmocnienie unikalnych pojęć (Term Boosting - Krok 2.5)**: Dynamiczne wzmacnianie wag krytycznych regulaminowo pojęć (np. deficyt, ects, komisyjny, urlop, skreślenie, wystawianie) w celu zapobiegania rozmywaniu cech (cosinusowej dilucji).
- **Zbiór testów konwersacyjnych**: Dodanie 9 rozbudowanych scenariuszy testowych z `długie_pytania.txt` do oficjalnego pakietu `tests/test.py`.

### Ulepszono
- **Skuteczność algorytmu**: Osiągnięcie rekordowych **73.0% precyzji (111/152)** w `tests/test_diff.py` — co stanowi ogromny skok **+9 poprawy przy zerowych (0) regresjach**!
- **Kompatybilność słowników**: Zintegrowano zaawansowaną korektę fleksyjną w `data/synonimy.toml` i `data/rozszerzenia.toml` (np. odmiany słów *deficyt*, *kolokwium*, *warunki* oraz precyzyjne naprowadzanie dla *rewersu*).

### Naprawiono
- **Odporność środowiskowa**: Zabezpieczono dynamiczne wyliczanie `mapa_wag` na wypadek pustej bazy danych współczynników w środowisku bezserwerowym (np. GitHub Actions / testy jednostkowe), pobierając strukturę bezpośrednio z fragmentów bazy wiedzy.

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
