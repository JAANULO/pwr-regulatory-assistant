# Plan Rozwoju i Audyt Architektury – Asystent PWr (v2)

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
- `PARTIAL` Obsługa potocznych pytań, slangu studenckiego i literówek (Słowniki i Levenshtein gotowe, brakuje Kart Szybkiej Odpowiedzi).
- **Implementacja (Słowniki):** Nasycenie bazy `SYNONIMY` potocyzmami (np. *dziekanka, warun, uwalenie, kolos*).
- **Implementacja (Wyszukiwarka):** Zwiększenie tolerancji algorytmu Levenshteina (`max_odleglosc=2`) dla słów dłuższych niż 8 znaków w funkcji `popraw_literowke()`.
- **Implementacja (Direct Answers):** Wprowadzenie mini-bazy "Karty Szybkiej Odpowiedzi", która w przypadku 100% pewności intencji zwraca krótką, z góry zdefiniowaną odpowiedź przed zacytowaniem regulaminu.

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

---

## 📂 Dokumenty Powiązane
- [PLAN.md](PLAN.md) - Główna mapa drogowa (funkcjonalności i produkt).
- [ARCHITEKTURA.md](ARCHITEKTURA.md) - Standardy kodu i wzorce projektowe (DDD, Refaktoryzacja).
- [CHANGELOG.md](../CHANGELOG.md) - Historia zrealizowanych zmian.
- [usprawnienie_pracy.md](usprawnienie_pracy.md) - Instrukcja prywatnej synchronizacji ustawień (Dotfiles).

> [!IMPORTANT]
> Projekt jest rozwijany z **całkowitym wyłączeniem gotowych modeli AI** (No NLP Libraries).
