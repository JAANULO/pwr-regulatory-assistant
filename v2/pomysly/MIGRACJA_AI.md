# Plan Migracji i Separacji Projektów

Ten dokument opisuje proces rozdzielenia repozytorium na dwa niezależne projekty:
1. **Regulatory Assistant** (Asystent Regulaminowy v2) – system produkcyjny BM25.
2. **Mini-GPT Research** – poligon doświadczalny dla modeli generatywnych (Transformer).

---

## 1. Repozytorium: Regulatory Assistant (Obecne)
To repozytorium zostaje oczyszczone ze wszystkich elementów ML/GPT, które nie są potrzebne do działania asystenta opartego na regulaminach.

### ✅ Pliki do ZACHOWANIA
Te pliki są kluczowe dla działania silnika BM25 i interfejsu webowego:
- `v2/app.py` – serwer Flask.
- `v2/core/`, `v2/infrastructure/`, `v2/domain/` – logika wyszukiwania.
- `v2/static/`, `v2/templates/` – frontend.
- `v2/scripts/asystent.py` – **WERYFIKACJA**: Skrypt CLI używa silnika BM25, nie GPT. Zostaje jako narzędzie diagnostyczne.
- `v2/scripts/debug.py` – narzędzie do testowania BM25.
- `MATEMATYKA.md` – opis matematyczny BM25 i Levenshteina.

### 🗑️ Pliki do USUNIĘCIA (Po migracji do nowego repo)
Te pliki dotyczą wyłącznie eksperymentów z GPT i PyTorchem:
- `v1/` – cały folder (stary prototyp).
- `shared/` – **WERYFIKACJA**: Zawiera kod transformera i tokenizera. Żaden plik z v2 (poza trainerem GPT) nie używa tych modułów.
- `v2/scripts/main.py` – **WERYFIKACJA**: To skrypt do treningu GPT. Zbędny dla silnika BM25.
- `v2/scripts/model_export.pt` – wagi starego modelu AI.
- `sprawdz_wszystko.py` – przestarzałe narzędzie, zastąpione przez CI/CD.
- `requirements.txt` (root) – dubel, używamy `v2/requirements.txt`.

---

## 2. Repozytorium: Mini-GPT Research (Nowe)
To repozytorium służy do archiwizacji i dalszego rozwoju silnika generatywnego.

### 📂 Pliki do PRZENIESIENIA (Kopiowania)
- Cały folder `v1/` (jako historia projektu).
- Folder `shared/` (jako baza architektury Transformer).
- `v2/scripts/main.py` (jako aktualny moduł treningowy).
- `MATEMATYKA.md` (kopia dokumentacji architektury).

---

## 🚀 Instrukcja Wykonania (Krok po Kroku)

### Krok 1: Przygotowanie Nowego Repozytorium
1. Stwórz nowe repozytorium na GitHub (np. `mini-gpt-pwr`).
2. Skopiuj do niego foldery `v1/` oraz `shared/`.
3. Skopiuj plik `v2/scripts/main.py` do głównego katalogu nowego repozytorium.
4. **Ważne**: W nowym `main.py` popraw ścieżki importów (usuń `v2_root` i odwołania do `core.bd`, jeśli nie chcesz przenosić bazy danych statystyk).

### Krok 2: Czyszczenie Obecnego Repozytorium
Po upewnieniu się, że pliki AI są bezpieczne w nowym miejscu, wykonaj w terminalu:

```powershell
# Usuwanie folderów
rm -r v1/
rm -r shared/

# Usuwanie plików GPT z v2
rm v2/scripts/main.py
rm v2/scripts/model_export.pt

# Usuwanie plików pomocniczych
rm sprawdz_wszystko.py
rm requirements.txt
rm requirements-dev.txt
```

### Krok 3: Weryfikacja Stabilności
1. Sprawdź, czy `v2/requirements.txt` nie zawiera `torch` (nie powinien).
2. Uruchom serwer: `python v2/app.py`.
3. Przetestuj wyszukiwanie w przeglądarce.

---

## ⚠️ Uwaga o Zależnościach
Asystent regulaminowy v2 po tej operacji stanie się znacznie lżejszy. Obraz Docker nie będzie już musiał instalować `torch` (chyba że jest on w `requirements.txt` – wtedy należy go stamtąd usunąć), co drastycznie przyspieszy deployment na Renderze.
