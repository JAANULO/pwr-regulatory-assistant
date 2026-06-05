"""
smoke_test.py – prosty test integracyjny (Smoke Test).
Sprawdza, czy aplikacja Flask uruchamia się poprawnie i czy endpoint /zapytaj odpowiada.
"""

import subprocess  # nosec B404
import time
import requests
import sys
import os


def run_test():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app_path = os.path.join(base_dir, "app.py")

    print(f"--- Uruchamianie Smoke Testu dla: {app_path} ---", flush=True)

    # Uruchomienie aplikacji w tle
    process = subprocess.Popen(  # nosec B603
        [sys.executable, "app.py"],
        cwd=base_dir,
        env={**os.environ, "FLASK_DEBUG": "0", "PORT": "5005"},
    )

    url = "http://localhost:5005/zapytaj"
    max_retries = 10
    success = False

    print("Oczekiwanie na start serwera (10s)...", flush=True)
    time.sleep(10)

    for i in range(max_retries):
        try:
            # Próbujemy zadać proste pytanie
            response = requests.post(
                url, json={"pytanie": "ile razy mozna zdawac egzamin?"}, timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if "odpowiedz" in data or "wstep" in data:
                    print(
                        f"[OK] Proba {i + 1}: Serwer odpowiedzial poprawnie na /zapytaj!",
                        flush=True,
                    )

                    # Test manifestu PWA
                    manifest_url = "http://localhost:5005/static/manifest.json"
                    print(
                        f"Sprawdzanie pliku manifestu PWA pod: {manifest_url}...",
                        flush=True,
                    )
                    manifest_resp = requests.get(manifest_url, timeout=5)
                    if manifest_resp.status_code == 200:
                        m_data = manifest_resp.json()
                        if (
                            m_data.get("display") == "standalone"
                            and m_data.get("start_url") == "/"
                        ):
                            print(
                                "[OK] Manifest PWA zostal poprawnie zwalidowany!",
                                flush=True,
                            )
                            # Test endpointu /lab/simulate
                            print("Sprawdzanie endpointu /lab/simulate...", flush=True)
                            try:
                                lab_resp = requests.post(
                                    "http://localhost:5005/lab/simulate",
                                    json={"max_combinations": 1},
                                    timeout=30,
                                )
                                if lab_resp.status_code == 200:
                                    print(
                                        "[OK] Endpoint /lab/simulate dziala poprawnie!",
                                        flush=True,
                                    )
                                    success = True
                                    break
                                else:
                                    print(
                                        f"[BLAD] Serwer zwrocil status {lab_resp.status_code} dla /lab/simulate",
                                        flush=True,
                                    )
                            except Exception as e:
                                print(
                                    f"[BLAD] /lab/simulate wyrzucil wyjatek: {e}",
                                    flush=True,
                                )
                        else:
                            print(
                                f"[BLAD] Manifest PWA ma niepoprawna strukture: {m_data}",
                                flush=True,
                            )
                    else:
                        print(
                            f"[BLAD] Serwer zwrocil status {manifest_resp.status_code} dla manifest.json",
                            flush=True,
                        )
            else:
                print(
                    f"Proba {i + 1}/{max_retries}: Serwer zwrocil status {response.status_code}",
                    flush=True,
                )
        except Exception as e:
            print(
                f"Proba {i + 1}/{max_retries}: Serwer jeszcze nie gotowy...", flush=True
            )

        time.sleep(3)

    # Sprzątanie
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()

    if success:
        print("--- Smoke Test ZALICZONY ---", flush=True)
        sys.exit(0)
    else:
        print(
            "--- BLAD: Smoke Test NIEZALICZONY (serwer nie odpowiedzial poprawnie) ---",
            flush=True,
        )
        sys.exit(1)


if __name__ == "__main__":
    run_test()
