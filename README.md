> 🇬🇧 [English](#-pwr-regulatory-assistant) &nbsp;|&nbsp; 🇵🇱 [Polski](#-asystent-regulaminowy-pwr)

---

# 🇬🇧 PWr Regulatory Assistant

> An information retrieval system for the study regulations of Wrocław University of Science and Technology (PWr).  
> Unlike classic LLMs that hallucinate — **this system always cites the exact source paragraph**.

An academic project built entirely from scratch — no NLP libraries (no sklearn, no Hugging Face, no external APIs).

---

All algorithms implemented **from scratch in pure Python**.

---

<p align="center">
  <img src="preview.png" alt="App Interface GUI" width="800">
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
         ↓
  answer + source: "§ 18. Exams"
```

All algorithms implemented **from scratch in pure Python**.

---

## Project Versions

### Version 1.0 – Generative Mini-GPT

A custom GPT architecture implementation written from scratch in PyTorch.  
The model learns to generate text based on a training sentence corpus.

**Features:**
- Transformer architecture with Multi-Head Attention mechanism
- Character-level tokenizer (43-token vocabulary)
- Batch training on GPU (CUDA)
- Model saving and loading with cache
- Compressed model export to GitHub (Git LFS)
- Conversation mode with memory of last 3 exchanges

**Model parameters:**

| Parameter | Value |
|---|---|
| Embedding dimension | 256 |
| Transformer layers | 6 |
| Multi-Head Attention heads | 8 |
| Total parameters | ~831,000 |
| Final loss (cross-entropy) | 0.084 |
| Training time (RTX 3060 Ti) | ~12 min |

---

### Version 2.0 – Regulatory Assistant

An extension of v1 with an information retrieval system for the PWr study regulations.  
Instead of generating answers from memory (risking hallucinations), the system first retrieves the correct regulation paragraph and then formulates a response.

**Features:**
- PDF parser (`pdfplumber`) for multiple files from `v2/data/` → separate JSON per document
- **BM25** algorithm from scratch (replaces TF-IDF — better accuracy for varying paragraph lengths)
- Cosine similarity for result ranking
- Levenshtein distance for typo correction (from scratch)
- Dictionary of ~180 Polish synonyms and word forms
- BM25 vector cache (`.pkl` file) — instant startup
- In-memory answer cache in API (`/zapytaj`) — TTL 1h, max 500 entries
- Direct paragraph retrieval by number (`§18`, `paragraph 18`) without BM25 recomputation
- **Sentence-level index** — instead of returning whole paragraphs, finds the exact sentence with the answer
- **Intent classifier** — detects question type (NUMBER / DATE / YES-NO / CONSEQUENCE / PROCEDURE) and returns a direct short answer, e.g. "You can take the exam **2 times**."
- **Number and date extraction via regex** — returns concrete values instead of regulation text
- **Conversation context memory** — follow-up questions like "and what if I fail?" refer to the previous paragraph
- Web interface (Flask + HTML/CSS/JS) with mobile support, light/dark mode toggle, sidebar with last 10 queries, and PDF export of chat
- CLI interface with conversation history
- **Professional Domain Layer** — data handled via `@dataclasses` (Strict Typing)
- **Repository Pattern** — clean separation between business logic and database (SQLite/PostgreSQL)
- **SQLite database** for statistics and feedback (`v2/data/asystent.db`)
- Text logs to `v2/logs/log.txt` (GUI + CLI runtime events)
- Feedback buttons 👍/👎 in GUI — saved to database; low-confidence negative feedback is appended to `v2/logs/do_poprawy.txt`
- Automated tests (`tests/test.py`) — regression set of 150 questions.

---

## Test Results

| Metric | Value |
|---|---|
| Test set size | 150 questions |
| Accuracy (correct paragraph) | **103/150 (68.6%)** |
| Response time | < 50 ms |
| Knowledge base size | 39 paragraphs |
| BM25 vocabulary | ~2165 unique words |
| Synonym dictionary entries | ~180 |

---

## Project Architecture

```
Mini-GPT/
├── .github/workflows/          ← CI/CD Autotests (GitHub Actions)
├── Dockerfile                  ← Container builder (Python + Gunicorn)
├── pyproject.toml              ← Linter config (Ruff PEP8)
├── preview.png                 ← Documentation GUI Image
├── shared/                     ← shared modules (v1 & v2)
│   ├── transformer.py          # GPT architecture (from scratch)
│   └── tokenizer.py            # character tokenizer
│
├── v1/                         ← generative version
│   ├── main.py                 # training + conversation mode
│   └── dane.json               # training data
│
└── v2/                         ← regulatory assistant
    ├── app.py                  # Flask server (GUI)
    ├── requirements.txt        # Python dependencies
    │
    ├── core/                   ← search & formatting logic
    │   ├── wyszukiwarka.py     # BM25 + Levenshtein + cosine
    │   ├── formatowanie.py     # response formatting
    │   ├── settings.py         # Config environments (.env load)
    │   └── bd.py               # Database connection layer (SQLite/Postgres)
    │
    ├── domain/                 ← business logic (Clean Architecture)
    │   ├── models.py           # Domain Data Classes
    │   ├── repositories/       # Repository Pattern (Data access)
    │   └── services/           # Application Services (Logic)
    │
    ├── infrastructure/         ← External tools & loaders
    │   ├── pdf_parser.py       # PDF parsing logic
    │   └── knowledge_loader.py # Knowledge base initialization
    │
    ├── data/                   ← Persistent storage
    │   ├── *.pdf               # source documents
    │   ├── *.json              # parsed knowledge files
    │   └── *.pkl               # BM25 / sentence index caches
    │
    ├── tests/
    │   └── test.py             # automated regression tests
    │
    ├── static/                 ← Frontend Assets
    └── templates/              ← HTML Views
```

---

## Installation & Usage

### Requirements

- Python 3.10+
- NVIDIA GPU with CUDA support (optional — also runs on CPU)

### Install dependencies

```bash
# PyTorch with CUDA 12.1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# other libraries
pip install numpy tqdm pdfplumber flask python-dotenv gunicorn ruff
```

### Environment Setup (`.env`)
To run the server securely with dashboard access, create a `.env` file in the main directory:
```env
ADMIN_TOKEN=your_secure_password_here
# Optional variables:
# DATABASE_URL=path/to/backup.db
```

### Docker Execution (Cloud Ready & Render-Safe)
The project is containerized for seamless cross-platform deployment. Use Docker to build an isolated environment (automatically scales the `$PORT` binding for Native Cloud hostings like Render!).

```bash
docker build -t pwr-assistant -f Dockerfile .
docker run -p 5000:5000 pwr-assistant
```

---

### Version 1.0 — Mini-GPT

```bash
cd v1
python main.py
```

The program automatically trains the model and starts conversation mode.  
On subsequent runs it loads the model from cache (training is skipped).

---

### Version 2.0 — Regulatory Assistant

**Step 1 — launch the GUI (it will parse PDFs automatically on first run):**

```bash
cd v2
python app.py
# → open http://localhost:5000
```

**Step 2 — run the tests:**

```bash
python tests/test.py
```

**Alternatively — CLI interface:**

```bash
python asystent.py
```

### Troubleshooting (v2)

- Red underline on `from core...` in IDE / Pylance Warnings
  - In VSCode: The project includes `pyrightconfig.json` and `.vscode/settings.json` which should fix this automatically.
- Relative import error (`attempted relative import with no known parent package`)
  - Do not run package modules by file path; use project entry points (`python app.py`, `python asystent.py`, `python -m tests.test`).
- Missing logs in root `logs/`
  - Runtime logs are stored in `v2/logs/log.txt` (not in repository root).

---

### CLI Commands

| Command | Description |
|---|---|
| `/szukaj <question>` | show top 3 paragraphs with similarity scores |
| `/historia` | show conversation history |
| `/zapomnij` | clear conversation history |
| `/info` | knowledge base info (paragraph count, vocabulary size) |
| `/pomoc` | list all commands |
| `koniec` | exit the program |

---

## Technologies Used

| Technology | Purpose |
|---|---|
| **Python 3.13** | entire backend |
| **PyTorch** | Transformer architecture, GPU training |
| **NumPy** | matrix operations |
| **pdfplumber** | PDF regulation parsing |
| **Flask** | HTTP server for GUI |
| **SQLite / Postgres** | statistics and feedback storage |
| **tqdm** | training progress bar |
| **Git LFS** | model file storage on GitHub |

**Algorithms implemented from scratch** (no external NLP libraries):
- **BM25** (Best Match 25 — improved TF-IDF used by Elasticsearch)
- Cosine similarity
- Levenshtein distance (typo correction)
- GPT / Transformer architecture
- Character-level tokenizer

---

## Hardware

| Component | Specification |
|---|---|
| CPU | Intel Core i7-11700F |
| GPU | NVIDIA RTX 3060 Ti 8 GB |
| RAM | 32 GB |
| OS | Windows 10 |

---

# 🇵🇱 Asystent Regulaminowy PWr

> System wyszukiwania informacji z regulaminu studiów Politechniki Wrocławskiej.  
> Zamiast halucynować jak klasyczne LLM — **zawsze podaje źródłowy paragraf regulaminu**.

Projekt akademicki zbudowany od zera — bez gotowych bibliotek NLP (bez sklearn, bez Hugging Face, bez zewnętrznych API).

---

Wszystkie algorytmy napisane **od zera w czystym Pythonie**.

---

<p align="center">
  <img src="preview.png" alt="Interfejs Asystenta GUI" width="800">
</p>

## Jak to działa

```
pytanie użytkownika: "ile razy można podejść do egzaminu?"
         ↓
  tokenizacja + normalizacja
  (usuwanie odmiany, literówek, polskich znaków)
         ↓
  BM25 — każde słowo pytania porównywane z każdym paragrafem
  (Best Match 25 — ulepsza TF-IDF o normalizację długości dokumentu)
         ↓
  podobieństwo cosinusowe → ranking paragrafów
         ↓
  odpowiedź + źródło: "§ 18. Egzaminy"
```

Wszystkie algorytmy napisane **od zera w czystym Pythonie**.

---


## Wersje projektu

### Wersja 1.0 – Mini-GPT generatywny

Własna implementacja modelu GPT napisana od zera bez gotowych frameworków NLP.  
Model uczy się generować tekst na podstawie zbioru zdań treningowych.

**Co zawiera:**
- Architektura Transformer z mechanizmem Multi-Head Attention
- Znakowy tokenizer (słownik 43 tokenów)
- Trening batchowy na GPU (CUDA)
- Zapis i wczytywanie modelu z cache
- Eksport skompresowanego modelu na GitHub (Git LFS)
- Tryb rozmowy z pamięcią ostatnich 3 wymian

**Parametry modelu:**

| Parametr | Wartość |
|---|---|
| Wymiar embeddingu | 256 |
| Liczba warstw Transformera | 6 |
| Głowice Multi-Head Attention | 8 |
| Parametry łącznie | ~831 000 |
| Strata końcowa (cross-entropy) | 0.084 |
| Czas treningu (RTX 3060 Ti) | ~12 min |

---

### Wersja 2.0 – Asystent Regulaminowy PWr

Rozbudowa v1 o system wyszukiwania informacji z regulaminu studiów Politechniki Wrocławskiej.  
Zamiast halucynować, model najpierw wyszukuje właściwy paragraf, a potem generuje odpowiedź.

**Co zawiera:**
- Parser PDF (`pdfplumber`) dla wielu plików z `v2/data/` → osobne JSON dla dokumentów
- Algorytm **BM25** napisany od zera (zastąpił TF-IDF — lepsza trafność dla różnej długości paragrafów)
- Podobieństwo cosinusowe do rankingu wyników
- Korekcja literówek algorytmem Levenshteina (napisanym od zera)
- Słownik ~180 synonimów i odmian dla języka polskiego
- Cache wektorów BM25 (plik `.pkl`) — natychmiastowy start
- Cache odpowiedzi w API (`/zapytaj`) — TTL 1h, max 500 wpisów
- Bezpośrednie trafienie paragrafu po numerze (`§18`, `paragraf 18`) bez liczenia BM25
- **Indeks na poziomie zdań** — system znajduje konkretne zdanie z odpowiedzią
- **Klasyfikator intencji** — wykrywa typ pytania (LICZBA / TERMIN / TAK-NIE / SKUTEK / PROCEDURA) i zwraca krótką bezpośrednią odpowiedź
- **Pamięć kontekstu rozmowy** — pytania następcze odnoszą się do poprzedniego paragrafu
- Interfejs webowy (Flask + HTML/CSS/JS) z obsługą mobile, panelem historii i eksportem rozmowy do PDF
- **Profesjonalna warstwa domeny** — dane obsługiwane przez `@dataclasses` (ścisłe typowanie)
- **Wzorzec Repozytorium** — separacja logiki od bazy danych (SQLite/PostgreSQL)
- **Baza SQLite** dla statystyk i feedbacku (`v2/data/asystent.db`)
- Testy automatyczne (`tests/test.py`) — zestaw regresyjny.

---

## Wyniki testów

| Metryka | Wartość |
|---|---|
| Rozmiar zestawu testowego | 150 pytań |
| Trafność (właściwy paragraf) | **103/150 (68.6%)** |
| Czas odpowiedzi | < 50 ms |
| Rozmiar bazy | 39 paragrafów |
| Słownik BM25 | ~2165 unikalnych słów |

---

## Architektura projektu

```
Mini-GPT/
├── .github/workflows/          ← Ciągła integracja z Git (Autotesty)
├── Dockerfile                  ← Kontener Docker (Python + Gunicorn)
├── pyproject.toml              ← Konfiguracja Lintera Ruff
├── shared/                     ← wspólne moduły (v1 i v2)
│
└── v2/                         ← asystent regulaminowy
    ├── app.py                  # serwer Flask (GUI)
    ├── requirements.txt        # zależności Pythona
    │
    ├── core/                   ← logika wyszukiwania i formatowania
    │   ├── wyszukiwarka.py     # BM25 + Levenshtein + cosinus
    │   ├── formatowanie.py     # formatowanie odpowiedzi
    │   └── bd.py               # Warstwa połączeń z bazą danych
    │
    ├── domain/                 ← logika biznesowa (Clean Architecture)
    │   ├── models.py           # Klasy danych (Dataclasses)
    │   ├── repositories/       # Wzorzec Repozytorium (SQL)
    │   └── services/           # Serwisy aplikacyjne (Logika)
    │
    ├── infrastructure/         ← Narzędzia zewnętrzne
    │   ├── pdf_parser.py       # Parsowanie PDF
    │   └── knowledge_loader.py # Inicjalizacja bazy wiedzy
    │
    ├── data/                   ← Dane i bazy
    │   ├── *.pdf               # dokumenty źródłowe
    │   ├── *.json              # baza wiedzy
    │   └── *.pkl               # cache indeksów
    │
    ├── tests/
    │   └── test.py             # testy automatyczne
    │
    ├── static/                 ← Frontend Assets
    └── templates/              ← Widoki HTML
```

---

##  Instalacja i uruchomienie

### Wymagania

- Python 3.10+
- NVIDIA GPU z obsługą CUDA (opcjonalnie)

### Instalacja zależności

```bash
# PyTorch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# pozostałe biblioteki
pip install numpy tqdm pdfplumber flask python-dotenv gunicorn ruff
```

### Konfiguracja środowiska (`.env`)
Utwórz plik `.env` i dodaj:
```env
ADMIN_TOKEN=twoje_bezpieczne_haslo
```

### Uruchomienie (Docker)
```bash
docker build -t asystent-pwr -f Dockerfile .
docker run -p 5000:5000 asystent-pwr
```

---

### Uruchomienie wersji 2.0

```bash
cd v2
python app.py
# → otwórz http://localhost:5000
```

### Rozwiązywanie problemów (v2)

- Błędy importów w IDE (Pylance):
  - Projekt zawiera gotową konfigurację w `.vscode/settings.json`, która automatycznie dodaje folder `v2` do ścieżki wyszukiwania.
- Błąd importu względnego:
  - Używaj `python -m tests.test` zamiast bezpośredniego wywołania pliku testu ze ścieżki.

---

##  Użyte Technologie

| Technologia | Zastosowanie |
|---|---|
| **Python 3.13** | backend |
| **PyTorch** | Transformer, trening GPU |
| **Flask** | serwer HTTP |
| **SQLite / Postgres** | statystyki i feedback |

**Algorytmy zaimplementowane od zera**:
- BM25 (Best Match 25)
- Podobieństwo cosinusowe
- Odległość Levenshteina
- Architektura Transformer / GPT
