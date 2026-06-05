
# Zarządzanie Kluczami API — Plan implementacji

## 1. Cel

Celem jest dodanie do projektu bezpiecznego systemu zarządzania kluczami API, który umożliwi zewnętrznym integratorom (np. osadzeniom JS na stronach) korzystanie z wybranych funkcji serwisu bez konieczności uruchamiania całego projektu lokalnie.

System ma zapewnić: generowanie, rotację i unieważnianie kluczy; autoryzację żądań przychodzących; limitowanie (rate limiting) i kwoty (quota); monitoring i podstawowe UI administracyjne.

## 2. Zakres

- Backend: endpoints CRUD dla kluczy, middleware autoryzacji, rate-limiter, logowanie użycia.
- Storage: bezpieczne przechowywanie hashów kluczy i metadanych w bazie danych.
- Integracja: przykładowy fragment JS do osadzenia (embed) i dokumentacja użycia.
- DevOps: konfiguracja środowisk (env vars), migracje DB, instrukcja wdrożenia (Docker).
- Testy: testy jednostkowe i integracyjne, scenariusze E2E (symulacja żądań).

## 3. Wymagania funkcjonalne

1. Generowanie nowego klucza z przypisanym zakresem uprawnień (scopes) i opcjonalną datą wygaśnięcia.
2. Przechowywanie tylko hashów kluczy; pełny klucz pokazany tylko raz przy tworzeniu.
3. Endpointy administracyjne: listowanie, tworzenie, rotacja (rotate), unieważnianie (revoke).
4. Każde żądanie API musi być weryfikowane poprzez middleware sprawdzające klucz (nagłówek `X-Api-Key` lub `Authorization: ApiKey <key>`).
5. Per-key rate limiting i quota z możliwością konfiguracji (requests/min, daily quota).
6. Logi użycia: kto, kiedy, endpoint, IP i rezultat (200/401/429).
7. Obsługa CORS dla embedów i ograniczenie originów (opcjonalnie whitelist).

## 4. Wymagania niefunkcjonalne / bezpieczeństwo

- Protokół: wymuszenie HTTPS na poziomie reverse-proxy / serwera.
- Hashowanie: użyć szybkiego algorytmu kryptograficznego (np. SHA-256 lub HMAC-SHA256 z globalnym sekretem). Algorytmy typu bcrypt są zbyt wolne dla kluczy API.
- Przechowywać w DB tylko hash; raw key generowany losowo (min. 32 bajty), wyświetlany tylko raz.
- Ograniczyć wycieki w logach (nie logować raw key). Logować jedynie id klucza/hash lub truncated.
- Wysokowydajne limitowanie: użyć Redis dla liczników i sliding window / fixed window.
- Rate limiter z fallbackem: jeśli Redis niedostępny — degrade gracefully (konserwatywne limitowanie lub odmowa).

## 5. Architektura komponentów

**Decyzja architektoniczna:** Obsługa kluczy API zostanie zaimplementowana jako **osobny podfolder/moduł w obecnym repozytorium** (monolit modularny, np. `api_gateway/`). Zapobiega to mieszaniu się logiki uwierzytelniania z główną aplikacją (`core/`, `domain/`), zachowując jednocześnie jedno wspólne wdrożenie (bez potrzeby stawiania nowych serwerów). Plik `app.py` zaimportuje ten moduł jedynie jako zgrabny middleware.

- API Key Service (wydzielony podfolder, np. `api_gateway/`) — generowanie, walidacja, rotacja, revokacja.
- Middleware: `api_key_auth` — odpala na początku requestu, weryfikuje klucz i ustawia `request.api_key_meta` przed wpuszczeniem do głównej logiki.
- Storage: tabele w głównej bazie (np. `api_keys`) + Redis dla liczników.
- Admin endpoints: zabezpieczone (np. admin token).
- Embed script (statyczny JS) — minimalny klient wysyłający żądania do twojego API z kluczem.

## 6. Model danych (propozycja tabeli `api_keys`)

- `id` : UUID
- `key_id` : skrócony identyfikator (np. 8-12 znaków) publiczny do referencji
- `key_hash` : tekst (hash klucza SHA-256)
- `created_by` : userid lub string
- `created_at` : timestamp
- `expires_at` : timestamp nullable
- `scopes` : JSON/text (lista dozwolonych akcji)
- `quota` : JSON (np. {"daily":1000, "monthly": null})
- `rate_limit` : JSON (np. {"per_min":20})
- `revoked` : boolean
- `meta` : JSON (opcjonalne pola, np. allowed_origins)
- `last_used_at` : timestamp nullable
- `usage_count` : integer (opcjonalne, do szybkiego podglądu)

Uwaga: dla skalowalności liczniki bieżącego użycia trzymać w Redis.

## 7. API — endpoints (szczegółowo)

Prefix: `/admin/api-keys` (secured endpoints dla admina)

1. `POST /admin/api-keys` — utwórz klucz
   - Body: `{ "scopes": ["ask","search"], "expires_at": "2026-12-01T00:00:00Z", "quota": {"daily":1000}, "allowed_origins": ["https://example.com"] }`
   - Response: `{ "key_id": "abc123", "api_key": "abc123.RAW-SECRET-ONLY-ONCE" , "meta": {...} }`
   - Raw klucz (prefiksowany `key_id`) pokazany tylko w odpowiedzi tworzenia.

2. `GET /admin/api-keys` — listuj klucze (bez raw key)

3. `GET /admin/api-keys/:key_id` — szczegóły metadanych

4. `POST /admin/api-keys/:key_id/rotate` — rotacja klucza
   - Generuje nowy raw key, unieważnia poprzedni (możliwość zachowania starego przez TTL)

5. `POST /admin/api-keys/:key_id/revoke` — revoke (ustaw `revoked=true`)

6. `POST /api/validate` — (opcjonalne publiczne) sprawdzenie ważności klucza (użyteczne przy debugowaniu)

Autoryzacja przy użyciu klucza dla końcówek użytkowych:
- Każde publiczne API sprawdza header: `Authorization: ApiKey <raw-key>` lub `X-Api-Key: <raw-key>`.

Przykładowa odpowiedź walidacji:
```
{ "valid": true, "key_id": "abc123", "scopes": ["ask"], "expires_at": null }
```

## 8. Middleware walidacji (pseudo)

1. Odczyt headeru `X-Api-Key` lub `Authorization`.
2. Jeśli brak -> 401.
3. Rozdzielenie klucza na `key_id` i `raw_secret` (np. po kropce).
4. Szybkie pobranie rekordu z bazy danych przy użyciu `key_id` po zoptymalizowanym indeksie. Jeśli brak -> 401.
5. Zahashowanie `raw_secret` (SHA-256) i porównanie z zapisanym w DB `key_hash` przy pomocy funkcji stałoczasowej (np. `hmac.compare_digest`).
4. Sprawdź `revoked` i `expires_at`.
5. Sprawdź `scopes` czy żądany endpoint jest dozwolony.
6. Wykonaj rate-limit / quota check (Redis) -> jeśli przekroczone -> 429.
7. Dodaj `request.api_key_meta` z metadanymi dla downstreamu.

## 9. Rate limiting i Quota

- Użyć Redis: klucz per-api-key + rolling window / token bucket.
- Miary: `requests/min`, `requests/day`.
- Implementacja: kombinacja sliding window (precision) i token bucket (dla burstów).
- Reakcja na przekroczenie: 429 + headery `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `Retry-After`.

## 10. Rotacja i unieważnianie

- Rotacja: endpoint generuje nowy raw key, nadrzędnie ustawia `revoked=true` dla starego lub ustawia `rotation_pending` by zaakceptować stare przez krótkie okno migracyjne (np. 5 minut).
- Unieważnianie natychmiastowe: ustaw `revoked=true`.

## 11. UI administracyjne i dokumentacja

- Minimalne admin UI: lista kluczy, przycisk create, rotate, revoke, widok metryk.
- Dokumentacja: plik `docs/klucze_api.md` + przykładowy snippet JS do embedowania.

Przykładowy embed JS (minimalny):

```js
// minimalny fragment do osadzenia (nie przechowuj raw key w public repo bez ograniczeń origin)
async function askQuestion(apiKey, prompt) {
  const res = await fetch('https://twoj-serwis.example/api/ask', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'ApiKey ' + apiKey
    },
    body: JSON.stringify({ prompt })
  });
  return res.json();
}
```

Uwaga: Zdecydowanie zaleca się użycie proxy po stronie integratora. Ograniczenie `allowed_origins` (CORS) chroni klucz tylko w przeglądarce i nie zapobiega jego skopiowaniu oraz użyciu poza nią (np. przez curl). Dla kluczy używanych w publicznym JS należy bezwzględnie stosować minimalne `quota` i restrykcyjny `rate_limit`.

## 12. Logging i monitoring

- Loguj każde zapytanie (bez raw key): `key_id`, endpoint, http_status, ip, latency.
- Eksportuj metryki do Prometheus/Grafana: liczba żądań per key, rate-limit hits, błędy 401/429.

## 13. Testy

- Testy jednostkowe modułu generowania/hashowania.
- Testy integracyjne endpointów admin (create/rotate/revoke) — sprawdź, że raw key działa tylko przed revokacją.
- Testy obciążeniowe dla rate-limitingu (skrypt symulujący wiele requestów).

## 14. Migracja i dane istniejące

- Jeśli istnieją użytkownicy: dodać kolumnę `api_keys` i migrację.
- Zapewnić skrypt migracyjny i dokumentację kroków (backup DB przed migracją).

## 15. Deployment i konfiguracja

- Env vars wymagane: `API_KEYS_SECRET` (opcjonalny pepper), `REDIS_URL`, `DATABASE_URL`, `RATE_LIMIT_CONFIG`.
- Docker: dodać usługi Redis do `docker-compose` / konfigurację produkcyjną.

## 16. Harmonogram i checklist (przykładowy, 2 tygodnie)

Tydzień 1:
- Dzień 1: Przegląd kodu (`app.py`), zaprojektowanie modelu danych i migracji.
- Dzień 2-3: Implementacja CRUD admin + generowanie klucza (bez rate-limit).
- Dzień 4: Implementacja middleware walidacji i testy manualne.
- Dzień 5: Dodanie Redis rate-limiter i quota.

Tydzień 2:
- Dzień 6-7: UI administracyjne + dokumentacja i przykładowe embedy.
- Dzień 8: Testy integracyjne i obciążeniowe.
- Dzień 9: Monitoring, logi, konfiguracja env.
- Dzień 10: Review i merge, przygotowanie instrukcji wdrożenia.

## 17. Ryzyka i mitigacje

- Wycieki kluczy (mitigacja: ograniczenia originów, quota, revoke, rotate).
- Skalowalność (mitigacja: Redis dla liczników, CDN/edge cache dla statycznych embedów).
- Nadużycia (monitoring i automatyczne blokady po anomaliach).

## 18. Kolejne kroki (konkretne zadania do implementacji)

1. Przejrzeć `app.py` i punkty wejścia API, zaproponować miejsca integracji middleware.
2. Dodać migrację DB dla tabeli `api_keys`.
3. Implementować admin endpoints i generowanie kluczy.
4. Dodać middleware walidacji i prosty rate-limiter Redis.
5. Napisać dokumentację i przykładowy embed.

---

Plik ten można traktować jako roadmapę — jeśli chcesz, mogę teraz: 1) przejrzeć `app.py` i wskazać dokładne miejsca integracji, albo 2) od razu zaimplementować moduł `core/api_keys.py` z podstawową funkcjonalnością.
