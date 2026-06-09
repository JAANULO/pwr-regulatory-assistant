import json
import re
import os
import requests

TOML_PATH = r"c:\Users\Janusz\Documents\GitHub\model\data\config\testy.toml"
BAZA_PATH = r"c:\Users\Janusz\Documents\GitHub\model\data\kb\baza_wiedzy.json"


def ask_local_ai(pytanie, tresc):
    prompt = f"""
Jesteś asystentem prawnym analizującym regulamin.
Zadanie: Znajdź, w którym dokładnie punkcie/ustępie paragrafu kryje się odpowiedź na zadane pytanie.

Paragraf:
{tresc}

Pytanie: {pytanie}

Zwróć TYLKO I WYŁĄCZNIE symbol tego punktu (np. "1.", "3)", "a)"). Nie pisz żadnych wyjaśnień.
Jeśli odpowiedź rozciąga się na cały paragraf i nie ma konkretnego punktu, zwróć słowo BRAK.
"""
    try:
        # Zakładamy lokalne Ollama z modelem llama3
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3", "prompt": prompt, "stream": False},
            timeout=10,
        )

        if response.status_code == 200:
            odp = response.json().get("response", "").strip()
            # Walidacja: chcemy tylko proste numeracje "1.", "19)", "a)"
            if odp == "BRAK" or re.match(r"^\d+[\.\)]|[a-z]\)$", odp):
                return odp
    except Exception as e:
        print(f"Błąd komunikacji z lokalnym AI: {e}")
        return "ERROR"
    return "BRAK"


def main():
    if not os.path.exists(BAZA_PATH):
        print("Nie znaleziono bazy wiedzy!")
        return

    with open(BAZA_PATH, "r", encoding="utf-8") as f:
        baza = json.load(f)

    with open(TOML_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    kb_map = {}
    for item in baza:
        if "tytul" in item:
            tytul_l = item["tytul"].lower()
            kb_map[tytul_l] = item["tresc"]

    new_lines = []
    current_q = None
    current_ocz = None

    print("Rozpoczynam analize pytan za pomoca lokalnego AI...")
    updated = 0

    i = 0
    while i < len(lines):
        line = lines[i]
        new_lines.append(line)

        match_q = re.match(r'^\s*pytanie\s*=\s*([\'"])(.*)\1', line)
        if match_q:
            current_q = match_q.group(2)

        match_ocz = re.match(r'^(\s*)oczekiwany\s*=\s*([\'"])(.*)\2', line)
        if match_ocz:
            current_ocz = match_ocz.group(3)
            indent = match_ocz.group(1)

            # Zobacz czy nastepna linia to juz punkt
            has_point = False
            if i + 1 < len(lines) and "oczekiwany_punkt" in lines[i + 1]:
                has_point = True

            if not has_point and current_q:
                # Szukamy tresci paragrafu
                tresc = None
                for t, tr in kb_map.items():
                    if current_ocz.lower() in t:
                        tresc = tr
                        break

                if tresc:
                    print(f"Analiza pytania: {current_q}")
                    punkt = ask_local_ai(current_q, tresc)
                    if punkt == "ERROR":
                        print("Przerywam skrypt z powodu bledu polaczenia z AI.")
                        break

                    if punkt and punkt != "BRAK":
                        new_lines.append(f'{indent}oczekiwany_punkt = "{punkt}"\n')
                        updated += 1
                        print(f" -> Dopasowano: {punkt}")
                    else:
                        print(" -> Brak jednoznacznego punktu")

            current_q = None
            current_ocz = None

        i += 1

    if updated > 0:
        with open(TOML_PATH, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        print(f"\nSukces! Dodano {updated} nowych punktow do testy.toml.")
    else:
        print("\nNie dodano zadnych nowych punktow.")


if __name__ == "__main__":
    main()
