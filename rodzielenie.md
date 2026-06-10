# Plan Rozdzielenia Architektury (Decoupling)

## Cel Projektu
Migracja aplikacji monolitycznej (Flask + Vanilla JS) do niezależnych warstw:
1. **Backend (API):** Kod Python (Flask) odpowiedzialny wyłącznie za logikę biznesową, autoryzację kluczy, modele AI i dostęp do baz danych.
2. **Frontend (SPA):** Czysty JavaScript, HTML i CSS, odpowiedzialny wyłącznie za renderowanie interfejsu (Widgetu) u klienta końcowego.

---

## Faza 1: Restrukturyzacja Repozytoriów
*Obecnie kod współdzieli jeden folder. Należy go fizycznie rozdzielić.*

1. **Inicjalizacja nowego repozytorium Frontendu:** - Utwórz na GitHubie repozytorium np. `pwr-assistant-widget`.
2. **Transfer zasobów statycznych:** - Przenieś do nowego repozytorium pliki interfejsu klienta (`.html`, `.css`, `.js` odpowiedzialny za czat) oraz assety statyczne (logo, grafiki).
3. **Izolacja Backendu:** - W pierwotnym repozytorium usuń wyeksportowane pliki frontendu z folderów `static/` i `templates/`. 
   - *Wyjątek:* Możesz pozostawić pliki HTML dla Panelu Administratora (`admin.html`, `admin_keys.html`), jeśli chcesz zarządzać kluczami bezpośrednio z poziomu adresu backendu.

## Faza 2: Modyfikacja kodu Backendu (Flask - `app.py`)
*Backend musi przestać wysyłać widoki, a zacząć działać jak klasyczne API RESTful.*

1. **Wymuszenie formatu JSON:**
   - Przejrzyj główne trasy API (endpointy). Upewnij się, że używają wyłącznie instrukcji `return jsonify(...)`, a nie `render_template(...)`.
2. **Zacieśnienie reguł CORS:**
   - W funkcji `@app.after_request` zamień aktualnie permisywną regułę `Access-Control-Allow-Origin: *` na ścisłą listę akceptowanych domen (np. `https://jaanulo.github.io`). Zablokuje to używanie Twojego API ze stron, których nie autoryzowałeś.
3. **Zmienne Środowiskowe (Environment Variables):**
   - Zweryfikuj, czy wszystkie dane wrażliwe (ciągi połączeń z PostgreSQL, Redis URL, `ADMIN_TOKEN`) są poprawnie wczytywane z systemu, a nie zahardkodowane w pliku `core/settings.py`.

## Faza 3: Modyfikacja kodu Frontendu (Vanilla JS)
*Strona internetowa musi stać się "głupim klientem", polegającym na serwerze API.*

1. **Zmiana ścieżek sieciowych (URL):**
   - Zlokalizuj w plikach `.js` wszystkie wystąpienia funkcji `fetch()`.
   - Zmień ścieżki względne (np. `fetch('/api/zapytaj')`) na absolutne (np. `fetch('https://adres-twojego-backendu.com/api/zapytaj')`).
2. **Implementacja autoryzacji (Klucze API):**
   - Zmodyfikuj żądania HTTP, dodając klucz API do nagłówków.
   - Składnia dla nagłówków: `{ 'Authorization': 'Bearer <TWÓJ_KLUCZ_API>' }`.
   - *Wskazówka:* Do kodu JS widgetu wprowadź zmienną konfiguracyjną (np. `const API_KEY = "..."`), aby klient mógł wkleić tam wygenerowany przez Ciebie klucz.
3. **Usunięcie logiki systemowej (Security):**
   - Usuń z kodu interfejsu (HTML/JS) wszystkie funkcje i panele służące do zarządzania wiedzą (np. funkcja `pokazBazeWiedzy()` i odpytywanie endpointu `/zrodla`). Zewnętrzny użytkownik nie powinien wiedzieć, z jakich plików budujesz wektory.

## Faza 4: Wdrożenie infrastruktury (Deployment)
*Uruchomienie obu projektów na oddzielnych serwerach.*

1. **Hosting Frontendu (GitHub Pages):**
   - W ustawieniach nowego repozytorium `pwr-assistant-widget` uruchom usługę GitHub Pages ze źródłem ustawionym na główną gałąź (np. `main`). 
2. **Hosting Backendu:**
   - Zmodyfikuj plik `requirements.txt`, upewniając się, że zawiera serwer WSGI odpowiedni na produkcję (np. `gunicorn`).
   - Wdróż repozytorium backendowe na wybraną platformę chmurową. Uzupełnij tam zmienne środowiskowe.
3. **Konfiguracja zapory (Firewall):**
   - W panelu bazy PostgreSQL (Dashboard) upewnij się, że nowo postawiony serwer backendowy ma uprawnienia IP do nawiązywania połączeń z bazą.

## Faza 5: Testy Integracyjne (End-to-End)
1. Z poziomu terminala wygeneruj nowy klucz testowy, korzystając z klasy `ApiKeyService`.
2. Otwórz zhostowaną stronę na GitHub Pages i wprowadź swój klucz.
3. Wykonaj pełen cykl pytania do asystenta.
4. Zbadaj konsolę w narzędziach deweloperskich (F12) – sprawdź, czy mechanizm CORS prawidłowo przepuścił żądanie `OPTIONS`, a następnie `POST`.
5. Sprawdź, czy `ApiKeyService` poprawnie zaktualizował licznik użycia (usage) w bazie PostgreSQL.