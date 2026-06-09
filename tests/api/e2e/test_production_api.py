import os
import pytest
import requests
from dotenv import load_dotenv

load_dotenv()

PROD_URL = os.getenv("TEST_PROD_URL", "https://model-wp08.onrender.com")
PROD_API_KEY = os.getenv("TEST_PROD_API_KEY")


@pytest.mark.skipif(
    not PROD_API_KEY, reason="Brak TEST_PROD_API_KEY w zmiennych srodowiskowych"
)
def test_prod_api_authorized():
    # Wysylamy zapytanie POST na chroniony endpoint z minimalnymi danymi
    response = requests.post(
        f"{PROD_URL}/api/zapytaj",
        json={"pytanie": "Test E2E"},
        headers={"X-Api-Key": PROD_API_KEY},
        timeout=15,
    )
    # Autoryzacja powinna przejść, więc status na pewno nie będzie 401
    assert response.status_code != 401


def test_prod_api_unauthorized():
    # Zapytanie bez klucza
    response = requests.post(
        f"{PROD_URL}/api/zapytaj", json={"pytanie": "Test E2E"}, timeout=15
    )
    assert response.status_code in [401, 403, 422]
