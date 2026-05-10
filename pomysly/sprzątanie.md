# 🧹 Plan Sprzątania Katalogu Głównego (Root)

Ten dokument opisuje planowaną reorganizację struktury plików w celu poprawy przejrzystości projektu. Obecnie w katalogu głównym znajduje się wiele plików pomocniczych, które można zgrupować.

## Proponowana Struktura

### 1. Katalog `/docs` (Dokumentacja)
Przeniesienie plików opisowych, które nie są krytyczne dla runtime'u aplikacji:
- `MATEMATYKA.md` -> `docs/MATEMATYKA.md`
- `CHANGELOG.md` -> `docs/CHANGELOG.md`
- `CONTRIBUTING.md` -> `docs/CONTRIBUTING.md`
- `preview.png` -> `docs/assets/preview.png`

### 2. Katalog `/docs/research` (Badania i Pomysły)
Przeniesienie obecnego folderu `pomysly/` do wnętrza dokumentacji, aby oddzielić kod od luźnych notatek:
- `pomysly/` -> `docs/research/`

### 3. Katalog `/deployment` (Opcjonalnie)
Pliki konfiguracyjne specyficzne dla hostingu/serwera:
- `Dockerfile` -> `deployment/Dockerfile` (wymaga zmiany w GitHub Actions)
- `gunicorn.conf.py` -> `deployment/gunicorn.conf.py`
- `runtime.txt` -> `deployment/runtime.txt`

## Niezbędne Zmiany w Kodzie (Po Sprzątaniu)

Po fizycznym przeniesieniu plików należy zaktualizować:

1. **Główny README.md**:
   - Zmienić linki do matematyki: `[MATEMATYKA.md](MATEMATYKA.md)` -> `[MATEMATYKA.md](docs/MATEMATYKA.md)`
   - Zmienić linki do changeloga: `[CHANGELOG.md](CHANGELOG.md)` -> `[CHANGELOG.md](docs/CHANGELOG.md)`
   - Zmienić ścieżkę do obrazka: `![Preview](preview.png)` -> `![Preview](docs/assets/preview.png)`

2. **GitHub Actions (`.github/workflows/`)**:
   - Jeśli przeniesiony zostanie `Dockerfile`, należy zaktualizować ścieżkę w kroku budowania obrazu.

3. **Gunicorn / Render**:
   - Jeśli przeniesione zostaną pliki konfiguracyjne deploymentu, należy zaktualizować komendę startową w panelu Render (np. wskazując nową ścieżkę do `gunicorn.conf.py`).

## Korzyści
- **Przejrzystość**: W katalogu głównym zostaną tylko kluczowe pliki (`app.py`, `requirements.txt`, `README.md`).
- **Profesjonalizm**: Struktura zgodna z nowoczesnymi standardami repozytoriów Open Source.
- **Łatwiejsza nawigacja**: Dokumentacja jest odseparowana od logiki biznesowej.
