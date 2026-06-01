> 🇬🇧 [English](#-pwr-regulatory-assistant) &nbsp;|&nbsp; 🇵🇱 [Polski](#-asystent-regulaminowy-pwr)

---

# 🇬🇧 PWr Regulatory Assistant

> An information retrieval system for the study regulations of Wrocław University of Science and Technology (PWr).
> Unlike classic LLMs that hallucinate — **this system always cites the exact source paragraph**.

An academic project built entirely from scratch — no external NLP libraries (no scikit-learn, no Hugging Face, no external APIs).

---

<p align="center">
  <img src="docs/assets/preview.png" alt="App Interface GUI" width="800">
</p>

## How It Works

```
user question: "how many times can I take an exam?"
         ↓
  tokenization + normalization
  (stemming, typo correction, diacritic removal)
         ↓
  BM25 — each word of the query compared against every paragraph
  (Best Match 25 — improves TF-IDF with document length normalization)
         ↓
  cosine similarity → paragraph ranking
  (threshold: 0.12 - 0.15)
         ↓
  answer + source: "§ 18. Exams"
```

---

## Project Status

### Regulatory Assistant (Active)

The current version of the project is a production-ready information retrieval system.
Instead of generating answers from memory, it uses a **RAG (Retrieval-Augmented Generation)** approach focused on precision.

**Key Features:**
- **BM25 Algorithm from scratch** — optimized for Polish legal texts ([see details in docs/MATEMATYKA.md](docs/MATEMATYKA.md)).
- **Levenshtein Distance** — custom implementation for typo correction.
- **Intent Classifier** — extracts numbers, dates, and consequences from paragraphs.
- **Diagnostics API** — built-in tools for production monitoring and error tracing.
- **Configuration & Hyperparameters** — **46 parameters** fully decoupled into [**`data/config/config.toml`**](data/config/config.toml) for easy tuning (BM25 constants, custom term boosts, static & dynamic chapter weights).
- **Release History** — track changes in [docs/CHANGELOG.md](docs/CHANGELOG.md).

---

## Quick Start

### Requirements
- Python 3.12+
- Docker (optional)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/JAANULO/pwr-regulatory-assistant.git
cd pwr-regulatory-assistant

# 2. Install dependencies (Production optimized)
pip install -r requirements.txt
```

### Running Locally

```bash
python app.py
# → open http://localhost:5000
```

---

## Diagnostics & Admin Tools

The project includes advanced diagnostics for the production environment (e.g., Render):
- **Debug Endpoint**: `/admin/debug?token=YOUR_TOKEN`
- **Error Tracing**: Append `?token=YOUR_TOKEN` to the URL to see full Python tracebacks in the chat UI if an error occurs.

---

## Technologies Used

| Technology | Purpose |
|---|---|
| **Python 3.13** | entire backend |
| **NumPy** | vector operations |
| **pdfplumber** | PDF regulation parsing |
| **Flask** | HTTP server for GUI |
| **SQLite / Postgres** | statistics and feedback storage |

---

# 🇵🇱 Asystent Regulaminowy PWr

> System wyszukiwania informacji z regulaminu studiów Politechniki Wrocławskiej.
> Zamiast halucynować jak klasyczne LLM — **zawsze podaje źródłowy paragraf regulaminu**.

Projekt akademicki zbudowany od zera — bez gotowych bibliotek NLP (bez sklearn, bez Hugging Face, bez zewnętrznych API).

---

## Jak to działa

```
pytanie użytkownika: "ile razy można podejść do egzaminu?"
         ↓
  tokenizacja + normalizacja
  (usuwanie odmiany, literówek, polskich znaków)
         ↓
  BM25 — każde słowo pytania porównywane z każdym paragrafem
         ↓
  podobieństwo cosinusowe → ranking paragrafów
         ↓
  odpowiedź + źródło: "§ 18. Egzaminy"
```

---

## Wersje projektu

### Asystent Regulaminowy (Aktywna)
Główny cel projektu to dostarczanie precyzyjnych informacji prawnych.
- **BM25 napisany od zera** (lepsza trafność niż TF-IDF).
- **Korekcja literówek Levenshteina** (od zera).
- **Indeks na poziomie zdań** — system znajduje konkretne zdanie z odpowiedzią.
- **Klasyfikator intencji** — wyciąga liczby i terminy bezpośrednio z tekstu.


---

## Instalacja i uruchomienie

### Wymagania
- Python 3.12+

### Szybki start
```bash
pip install -r requirements.txt
python app.py
```

### Wyniki testów 
| Metryka | Wartość |
|---|---|
| Rozmiar zestawu testowego | 170 pytań |
| Trafność (właściwy paragraf) | **129/170 (75.8%)** |
| Czas odpowiedzi | < 50 ms |

### Konfiguracja i Hiperparametry
Wyszukiwarka posiada **47 konfigurowalnych parametrów** wydzielonych całkowicie z kodu do deklaratywnego pliku [**`data/config/config.toml`**](data/config/config.toml). Pozwala to na precyzyjne strojenie silnika bez modyfikacji logiki Pythona:
- **`[bm25]`** (3 parametry): współczynniki `k1`, `b` oraz mnożnik wagi synonimów `synonimy_waga`.
- **`[term_boosts]`** (32 parametry): podbicia wag IDF dla specyficznych słów kluczowych regulaminu (np. `deficyt`, `ects`, `komisyjny`).
- **`[mapa_wag_statyczna]`** (3 parametry): stałe podbicia punktacji dla najważniejszych rozdziałów.
- **`[mapa_wag_dynamiczna]`** (8 parametrów): warunkowe podbicia rozdziałów aktywowane obecnością powiązanych tokenów w zapytaniu.

#### Automatyczna Symulacja
Projekt wspiera wbudowany moduł siatki optymalizacyjnej (Grid Search). Aby uruchomić optymalizator:
```bash
python scripts/symulacja.py
```
Symulacja testuje dziesiątki parametrów na zestawie z `data/config/testy.toml` w poszukiwaniu najlepszego wyniku.

---

## Architektura projektu

```
├── docs/                       ← Dokumentacja techniczna i changelog
│   ├── assets/                 ← Obrazy i grafiki
│   └── research/               ← Notatki i pomysły (dawniej pomysly/)
├── deployment/                 ← Pliki wdrożeniowe (Docker, Gunicorn)
│   ├── Dockerfile
│   ├── .dockerignore
│   └── gunicorn.conf.py
├── app.py                      ← Serwer API Flask
├── core/                       ← Algorytmy i ustawienia
├── domain/                     ← Logika biznesowa i repozytoria
├── infrastructure/             ← Loadery i infrastruktura
├── static/                     ← Frontend (JS, CSS)
├── templates/                  ← Frontend (HTML)
├── data/                       ← Konfiguracja, bazy danych, bazy wiedzy (SoC)
│   ├── config/                 ← Pliki konfiguracyjne TOML
│   ├── database/               ← Baza SQLite i pliki cache .pkl (ignorowane)
│   └── kb/                     ← Pliki bazy wiedzy (.json, .pdf)
└── tests/                      ← Testy i weryfikacja
```

---
