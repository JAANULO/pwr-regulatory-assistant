# Jak wnosić wkład do projektu

Dziękuję za zainteresowanie projektem **Asystent Regulaminowy PWr**!  
Poniżej znajdziesz wszystko, czego potrzebujesz, żeby uruchomić projekt lokalnie i wprowadzić zmiany.

---

## Uruchomienie lokalne

### Wymagania
- Python 3.11+
- pip

### Instalacja

```bash
git clone https://github.com/JAANULO/model.git
cd model/v2
pip install -r requirements.txt
```

### Uruchomienie serwera deweloperskiego

```bash
cd v2
python app.py
# Aplikacja dostępna pod: http://localhost:5000
```

---

## Struktura projektu

```
model/
├── v2/
│   ├── app.py              # Serwer Flask – główny punkt wejścia
│   ├── core/
│   │   ├── wyszukiwarka.py # Algorytm BM25 + TF-IDF
│   │   ├── stemmer.py      # Stemmer + oboczności językowe
│   │   ├── slowniki.py     # Słownik synonimów i rozszerzeń
│   │   └── formatowanie.py # Formatowanie odpowiedzi
│   ├── data/               # Baza wiedzy JSON (przetworzona z PDF)
│   ├── templates/          # Szablony HTML (Jinja2)
│   ├── static/             # CSS, JS, obrazki
│   ├── tests/              # Testy jednostkowe BM25
│   └── logs/               # Logi słabych odpowiedzi
└── .github/workflows/      # CI/CD GitHub Actions
```

---

## Uruchamianie testów

```bash
cd v2
python tests/test.py
```

Oczekiwany wynik: `Wyniki: X/150 testów zaliczonych`

---

## Konwencja commitów

Projekt używa [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | Kiedy używać |
|--------|-------------|
| `feat:` | Nowa funkcjonalność |
| `fix:` | Naprawa błędu |
| `chore:` | Zmiany konfiguracji, narzędzia |
| `docs:` | Tylko dokumentacja |
| `test:` | Dodanie/zmiana testów |
| `refactor:` | Refaktoryzacja bez zmiany funkcjonalności |

Przykład: `fix: popraw tokenizację dla pytań z literówkami`

---

## Zasady kodu

- **Python**: PEP 8, wcięcia 4 spacje, max. 100 znaków na linię
- **HTML/JS**: wcięcia 2 spacje
- **Zero zewnętrznych bibliotek NLP** — algorytmy BM25, Levenshteina i stemmer są napisane od zera
- Linter: `ruff check v2/`
