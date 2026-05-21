# 📋 Plan Wdrożenia: Oczyszczenie Projektu Guardian

Plan ten opisuje kroki niezbędne do usunięcia zbędnych wrapperów, uproszczenia komentarzy na bardziej inżynierskie i akademickie oraz doprecyzowania typowania danych w kluczowych modułach algorytmicznych projektu **Guardian (Asystent Regulaminowy PWr)**.

---

## 1. Zakres Refaktoryzacji (Co Zmieniamy?)

Refaktoryzacja skupia się na usunięciu specyficznych struktur kodu i komentarzy typowych dla AI, pozostawiając system w pełni gotowym do akademickiej obrony inżynierskiej.

### A. Wyszukiwarka (`core/wyszukiwarka.py`)
1. **Typowanie:**
   - Poprawa definicji typów dla struktur cache:
     ```python
     _cache_literowek: dict[str, str] = {}
     ```
2. **Uproszczenie Metod BM25:**
   - Wyeliminowanie pustych wrapperów `oblicz_idf` oraz `zbuduj_wektory` zachowanych "dla kompatybilności".
   - Zastąpienie ich bezpośrednim importem i wywoływaniem zunifikowanych funkcji `oblicz_idf_bm25` oraz `zbuduj_wektory_bm25`.
3. **Korekta Komentarzy:**
   - Zmiana poetyckiego opisu *"błędu samotnej wyspy"* na: `# zabezpieczenie przed pętlami własnymi (autorelacja tokenu)`.
   - Zmiana opisu *"potężniejszych kółek"* na: `# Skalowanie rozmiaru węzła na podstawie stopnia (node degree)`.
   - Zastąpienie zwrotu *"zgodności regresyjnej"* jasnym opisem technicznym obsługi zapytań jednozdaniowych.

### B. Konfiguracja Wywołań (`infrastructure/knowledge_loader.py` & `core/indeks_zdan.py`)
- Zmiana importów i wywołań przestarzałych funkcji `oblicz_idf` i `zbuduj_wektory` na poprawne wywołania `oblicz_idf_bm25` i `zbuduj_wektory_bm25`.

---

## 2. Plan Weryfikacji (Jak Sprawdzamy?)

Po dokonaniu modyfikacji w plikach wykonamy następujące kroki testowe w celu wyeliminowania regresji (wszelkie testy uruchamiamy lokalnie):

1. **Uruchomienie Testów Ewaluacyjnych:**
   ```bash
   python tests/test.py
   ```
   *Oczekiwany rezultat:* Brak regresji, minimum 129/170 testów zaliczonych pozytywnie (jak w wersji bazowej).

2. **Uruchomienie Testu Integracyjnego (Smoke Test):**
   ```bash
   python tests/smoke_test.py
   ```
   *Oczekiwany rezultat:* Serwer Flask uruchamia się poprawnie w tle na dedykowanym porcie, poprawnie odpowiada na zapytania testowe HTTP POST i kończy działanie bez błędów.
