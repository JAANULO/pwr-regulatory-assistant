import requests
import os
import uuid
from dotenv import load_dotenv

load_dotenv()
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "dev-token-zmien-mnie")
BASE_URL = "http://localhost:5000"


def test_api_keys():
    print("--- 1. Tworzenie klucza ---")
    create_payload = {
        "name": f"test_script_key_{uuid.uuid4()}",
        "scopes": ["all"],
        "quota": {"daily": 1000},
        "rate_limit": {"per_min": 3},
        "created_by": "test_script",
    }
    r = requests.post(
        f"{BASE_URL}/admin/api-keys?token={ADMIN_TOKEN}",
        json=create_payload,
        timeout=10,
    )
    if r.status_code != 201:
        print(f"Błąd przy tworzeniu klucza: {r.status_code} - {r.text}")
        return

    data = r.json()
    key_id = data["key_id"]
    api_key = data["api_key"]
    print(f"Utworzono klucz! ID: {key_id}")
    print(f"Pełny klucz (tylko raz widoczny): {api_key}")

    print("\n--- 2. Wywołanie /api/zapytaj bez klucza ---")
    r2 = requests.post(
        f"{BASE_URL}/api/zapytaj", json={"pytanie": "jak napisać podanie"}, timeout=10
    )
    print(f"Status (oczekiwane 401): {r2.status_code} - {r2.text}")

    print("\n--- 3. Wywołanie /api/zapytaj z kluczem ---")
    headers = {"X-Api-Key": api_key}
    r3 = requests.post(
        f"{BASE_URL}/api/zapytaj",
        json={"pytanie": "co to jest USOS"},
        headers=headers,
        timeout=10,
    )
    print(f"Status (oczekiwane 200): {r3.status_code}")
    if r3.status_code == 200:
        print("Zapytanie udane.")

    print("\n--- 4. Test rate-limitu (limit 3/min) ---")
    for i in range(4):
        r4 = requests.post(
            f"{BASE_URL}/api/zapytaj",
            json={"pytanie": "pytanie testowe"},
            headers=headers,
            timeout=10,
        )
        print(f"Zapytanie #{i + 1}: Status {r4.status_code}")

    print("\n--- 5. Listowanie kluczy (admin) ---")
    r5 = requests.get(f"{BASE_URL}/admin/api-keys?token={ADMIN_TOKEN}", timeout=10)
    print(f"Liczba kluczy w systemie: {len(r5.json())}")

    print("\n--- 6. Revokacja klucza ---")
    r6 = requests.post(
        f"{BASE_URL}/admin/api-keys/{key_id}/revoke?token={ADMIN_TOKEN}", timeout=10
    )
    print(f"Status revokacji: {r6.status_code} - {r6.json()}")

    print("\n--- 7. Wywołanie /api/zapytaj na odwołanym kluczu ---")
    r7 = requests.post(
        f"{BASE_URL}/api/zapytaj", json={"pytanie": "test"}, headers=headers, timeout=10
    )
    print(f"Status (oczekiwane 401): {r7.status_code} - {r7.text}")


if __name__ == "__main__":
    test_api_keys()
