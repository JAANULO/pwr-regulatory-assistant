# Plan Rozwoju i Audyt Architektury – Asystent PWr 

Ten dokument zawiera wizję rozwoju projektu, uporządkowaną według poziomu trudności implementacji oraz aktualnego statusu prac.

## Legenda statusów
- `DONE` — funkcja zaimplementowana i dostępna
- `PARTIAL` — funkcja wdrożona częściowo lub z ograniczeniami
- `TODO` — funkcja planowana

---

## Poziom 0: Stabilność i Weryfikacja (Krytyczne)

### 0.1 Naprawa skryptów weryfikacyjnych (Windows / Unicode)
- `DONE` Testy działają stabilnie na Windows (UTF-8, ścieżki bezwzględne).

### 0.2 Test Diff Tool (Analiza Regresji)
- `DONE` Narzędzie `tests/test_diff.py` gotowe. baseline.json wygenerowany.

### 0.3 Wizualny feedback "Thinking" (UI)
- `DONE` Dodano pulsujący tekst "Szukam informacji..." i odświeżono animację dots.

---

## Poziom 1: Wydajność i Infrastruktura (Średnio łatwe)

### 1.1 Bezpieczeństwo i Konfiguracja (.env)
- `DONE` Migracja `ADMIN_TOKEN` oraz ścieżek baz danych do pliku `.env` (python-dotenv).

 ### 1.2 Responsywność i Mobilność (Mobile First)
 - `TODO` Dostosowanie interfejsu do urządzeń mobilnych (Aplikacja webowa/PWA).
 - **Implementacja:** Meta-tagi viewport, elastyczne kontenery (Flexbox/Grid), obsługa gestów dotykowych dla bocznego menu.

 ### 1.3 Separacja danych słownikowych (Synonimy i Rozszerzenia do TOML)
 - `DONE` Wyodrębnienie `SYNONIMY` oraz `ROZSZERZENIA` z pliku `core/slowniki.py` do zewnętrznych plików TOML w folderze `data/`.
 - **Implementacja:** Utworzenie `data/synonimy.toml` i `data/rozszerzenia.toml`, a następnie przepisanie `core/slowniki.py`, aby dynamicznie wczytywało te pliki przy użyciu wbudowanej biblioteki `tomllib` podczas startu aplikacji. Ułatwi to edycję i komentowanie słowników bez konieczności modyfikacji kodu źródłowego.

 ### 1.4 Automatyczne inwalidowanie cache przy zmianach słowników (Dynamic Cache Invalidation)
 - `DONE` Zabezpieczenie spójności indeksu BM25 przy zmianach definicji słownikowych.
 - **Implementacja:** Dodanie plików `data/synonimy.toml` oraz `data/rozszerzenia.toml` do mechanizmu sprawdzania `baza_mtime` w `infrastructure/knowledge_loader.py`. Jeśli jakikolwiek plik TOML słownika zostanie zmodyfikowany, stary plik cache `.pkl` zostanie automatycznie uznany za przestarzały i przebudowany przy starcie aplikacji.


---

## Poziom 2: Algorytmy i UX: Laboratorium (Wymagające)

### 2.1 Laboratorium Regulaminowe (Tryb Symulacji)
- `DONE` Interaktywne badanie wpływu parametrów na wykresach liniowych (Baseline vs Delta).
- **Backend:** Refaktoryzacja `Wyszukiwarka.szukaj`, aby przyjmowała `virtual_params` (ad-hoc).
- **Obsługiwane parametry:** `synonym_weight` (siła synonimów), `confidence_threshold` (próg pewności), `bm25_k1` oraz `bm25_b` (czułość na długość tekstu).
- **Frontend (`lab.html`):** Dashboard z suwakami i Chart.js. Dwie linie na wykresie: szara (oryginalna) i neonowa (symulacja).
- **Eksport:** Przycisk pobierania aktualnej konfiguracji suwaków do pliku JSON/TXT.
- **Odniesienie:** [symulacja.md](symulacja.md)

### 2.2 Poprawa słownika (§ECTS, §Praktyki)
- `DONE` Rozbudowa synonimów dla nowych, trudnych paragrafów regulaminu.

### 2.3 Żwawe odpowiedzi na "luźno" zadane pytania (Slang i Fast Track)
- `DONE` Obsługa potocznych pytań, slangu studenckiego i literówek (Słowniki i Levenshtein gotowe, wdrożono zrekonstruowane Karty Szybkiej Odpowiedzi oparte na § 2 Słownika Pojęć).
- **Implementacja (Słowniki):** Nasycenie bazy `SYNONIMY` potocyzmami (np. *dziekanka, warun, uwalenie, kolos*).
- **Implementacja (Wyszukiwarka):** Zwiększenie tolerancji algorytmu Levenshteina (`max_odleglosc=2`) dla słów dłuższych niż 8 znaków w funkcji `popraw_literowke()`.
- **Implementacja (Direct Answers):** Wdrożenie inteligentnego dopasowywania dwuetapowego i natychmiastowego serwowania definicji słownikowych z § 2 bez zmian w kodzie warstwy graficznej.

### 2.4 Fonetyczna tolerancja na literówki (Homophonic Polish Fuzzy Search)
- `DONE` Zwiększenie celności korekcji literówek o błędy fonetyczne typowe dla języka polskiego.
- **Implementacja:** Wdrożenie uproszczonego algorytmu upraszczania fonetycznego (np. zamiana `ch`->`h`, `rz`->`z`, `sz`->`s`, `ó`->`u` na kopiach słów) przed obliczeniem odległości Levenshteina. Zapewni to bezbłędne znajdowanie synonimów nawet przy grubych błędach ortograficznych (np. "rezygnacja" wpisane jako "rezignacja").

### 2.5 Zwiększanie poprawności wyszukiwania (Term Boosting)
- `DONE` Poprawa trafności zapytań poprzez wzmacnianie unikalnych słów kluczowych o krytycznym znaczeniu regulaminowym.
- **Implementacja:** Dodanie mechanizmu wagowania unikalnych terminów (np. `deficyt`, `ects`, `komisyjny`, `urlop`, `skreslenie`) w `Wyszukiwarka.szukaj()`. Jeśli w zapytaniu pojawi się zdefiniowane słowo kluczowe, jego wartość IDF w wektorze BM25 zostanie dynamicznie pomnożona (np. `* 3.0`), gwarantując, że asystent precyzyjnie trafi w odpowiedni paragraf pomimo obecności innych, ogólnych słów w zdaniu.

---

## Poziom 3: Architektura i Use Cases (Trudne)


### 3.2 Algorytmiczny "Did you mean?"
- `TODO` Inteligentne sugestie oparte na Grafie Relacji przy niskiej pewności wyników.

### 3.3 Angielski / polski tryb (Bilingual Mode) - narazie pomijamy
- `TODO` Wsparcie dla dwóch języków poprzez oddzielne statyczne indeksy BM25.
- **Implementacja (Baza):** Wygenerowanie drugiego pliku bazy danych (np. `baza_wiedzy_en.json`).
- **Implementacja (Słowniki):** Stworzenie oddzielnych zmiennych konfiguracyjnych `SYNONIMY_EN` i `ROZSZERZENIA_EN` w pliku `core/slowniki.py` oraz dodanie angielskich stopwords.
- **Implementacja (Interfejs):** Przycisk przełączania języka na stronie głównej przekazujący parametr `?lang=en` do API.
- **Implementacja (Wyszukiwarka):** Przebudowa silnika do obsługi wielu instancji indeksu i wybór bazy w locie na podstawie parametru językowego (najbardziej wymagające architektonicznie).

### 3.4 Automatyczna walidacja spójności słowników (Dictionary Integrity CI/CD)
 - `DONE` Zabezpieczenie potoku wdrożeniowego (CI/CD) przed błędnymi wpisami w TOML.
 - **Implementacja:** Stworzenie skryptu testowego (np. `tests/validate_dictionaries.py`) sprawdzającego:
   1. Poprawność składni plików `synonimy.toml` i `rozszerzenia.toml`.
   2. Wykrywanie cykli w synonimach (np. `A` mapuje się na `B`, a `B` z powrotem na `A`, co wywołałoby nieskończoną pętlę normalizacji).
   3. Walidację duplikatów kluczy i pustych wartości. Zintegrowanie skryptu z GitHub Actions

### 3.5 Obsługa złożonych zapytań konwersacyjnych (Conversational Queries & Query Segmentation)
 - `DONE` Poprawa radzenia sobie z długimi wypracowaniami studenckimi (tzw. "conversational queries") zawierającymi szum informacyjny.
 - **Implementacja:** Wdrożenie dwuetapowej analizy zapytania w `Wyszukiwarka.szukaj()`:
   1. Podział długiego zapytania użytkownika na pojedyncze zdania (Query Segmentation).
   2. Ocenianie każdego zdania niezależnie przy użyciu BM25 i sumowanie ich wektorów podobieństwa (z pominięciem powitań/szumu grzecznościowego), aby zapobiec "rozmywaniu" trafności zapytań.
   3. Dodanie pakietu testów konwersacyjnych (złożonych z 2-3 zdań) do `tests/test.py` w celu walidacji regresji.
---

## Poziom 4: Refaktoryzacja i Optymalizacje Algorytmiczne (Wymagające)

### 4.1 Podłączenie Stemmera jako fallback celności
- `TODO` Integracja pliku `scratch/stemmer.py` z wyszukiwarką w celu obsługi skomplikowanych odmian fleksyjnych języka polskiego.
- **Implementacja:** Przeniesienie `scratch/stemmer.py` z powrotem do `core/` i wywołanie funkcji `stemuj` w `Wyszukiwarka.szukaj()` w formie inteligentnego fallbacku. Uruchamiany automatycznie, gdy pierwotne wyszukiwanie oparte o synonimy i odległość Levenshteina nie zwraca wyników o wystarczającej pewności (np. podobieństwo `< 0.12`). Rozwiązanie to drastycznie podniesie celność wyszukiwania i wyeliminuje problemy z rzadkimi formami deklinacyjnymi bez spowalniania standardowej ścieżki wyszukiwania.

### 4.2 Odchudzenie warstwy bazodanowej core/bd.py
- `TODO` Ujednolicenie architektury bazodanowej poprzez eliminację proceduralnych wrapperów.
- **Implementacja:** Pełne przejście na wykorzystanie obiektów Repozytoriów z `domain/repositories/` wstrzykiwanych bezpośrednio przez Kontener DI w miejscach wywołań (w endpointach `app.py` oraz serwisach domenowych), eliminując redundantne, proceduralne funkcje pośredniczące z `core/bd.py`. Szczegóły techniczne i standardy znajdują się w punkcie **[ARCHITEKTURA.md § 1.6](ARCHITEKTURA.md#16-pe%C5%82na-eliminacja-proceduralnego-wrappera-bazy-danych-corebdpy)**.

---

## Poziom 5: Rozszerzenie Systemu (Bardzo trudne)

### 5.1 GUI do zarządzania regulaminami (PDF -> JSON)
- `TODO` Automatyzacja dodawania nowych dokumentów przez interfejs przeglądarkowy.

### 5.2 Weryfikacja plików tekstowych z regulaminem
- `TODO` Weryfikacja spójności dostarczonych plików użytkownika z przepisami uczelnianymi.
- **Implementacja (API):** Nowy endpoint przyjmujący pliki (np. `.pdf`, `.txt`) do ekstrakcji czystego tekstu.
- **Implementacja (Logika):** Segmentacja tekstu pliku na zdania/akapity i iteracyjne przepuszczanie każdego przez funkcję `wyszukiwarka.szukaj()`.
- **Implementacja (Wynik):** Zestawienie i wyświetlenie ustrukturyzowanego raportu porównawczego w UI, prezentującego zdania wsadowe zestawione z dopasowanymi paragrafami regulaminu (na podstawie wyniku BM25).

 ---

 ## Poziom 6: Administracja i Diagnostyka

 ### 6.1 Tryb Diagnostyczny (Admin Health Check)
 - `TODO` Rozbudowany system raportowania błędów dla administratora w przypadku awarii hostingu.
 - **Implementacja (Backend):** Endpoint `/health` zwracający stan połączenia z bazą, dostępność plików JSON oraz status procesów.
 - **Implementacja (UI):** Specjalny widok "Admin Debug" (dostępny po tokenie), który pokazuje logi błędów serwera bezpośrednio w przeglądarce, gdy API zwraca 500 lub brak połączenia.

 ### 6.2 Wydzielenie promptów LLM do pliku konfiguracyjnego (Prompt Engineering Decoupling)
 - `DONE` Przeniesienie wszystkich wielolinijkowych szablonów promptów (do generowania pytań, oceniania trafności, analizy błędów) z kodu źródłowego `tests/auto_tester.py` do zewnętrznego pliku `tests/prompts.toml`.
 - **Implementacja:** Odczytywanie pliku `tests/prompts.toml` przy starcie auto-testera i dynamiczne uzupełnianie zmiennych szablonu za pomocą funkcji `.format()` lub modułu `string.Template`. Ułatwi to dostrajanie zachowania modeli AI bez ingerencji w logikę skryptu Pythona.

---

## 📂 Dokumenty Powiązane
- [PLAN.md](PLAN.md) - Główna mapa drogowa (funkcjonalności i produkt).
- [ARCHITEKTURA.md](ARCHITEKTURA.md) - Standardy kodu i wzorce projektowe (DDD, Refaktoryzacja).
- [CHANGELOG.md](../CHANGELOG.md) - Historia zrealizowanych zmian.
- [usprawnienie_pracy.md](usprawnienie_pracy.md) - Instrukcja prywatnej synchronizacji ustawień (Dotfiles).

> [!IMPORTANT]
> Projekt jest rozwijany z **całkowitym wyłączeniem gotowych modeli AI** (No NLP Libraries).
