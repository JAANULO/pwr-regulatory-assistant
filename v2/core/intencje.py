"""
intencje.py – klasyfikator intencji pytania.
Rozpoznaje typ pytania i wyciąga konkretną wartość z odpowiedzi.

Typy intencji:
  LICZBA     – "ile razy", "ile dni"     → szukaj liczby w odpowiedzi
  TERMIN     – "kiedy", "do kiedy"       → szukaj daty/terminu
  TAK_NIE    – "czy mogę", "czy można"   → szukaj warunku tak/nie
  SKUTEK     – "co grozi", "co się stanie" → szukaj konsekwencji
  PROCEDURA  – "jak", "w jaki sposób"   → szukaj kroków
  DEFINICJA  – "co to jest", "czym jest" → szukaj definicji
  OGOLNE     – wszystko inne
"""

import re


# ── wzorce intencji ───────────────────────────────────────────────────────────

INTENCJE = [
    (
        "LICZBA",
        [
            "ile razy",
            "ile tygodni",
            "ile semestr",
            "ile terminu",
            "ile godzin",
            "ile punkt",
            "ile lat",
            "ile osob",
            "ile miesiec",
            "ile razy mozna",
        ],
    ),
    (
        "TERMIN",
        [
            "kiedy",
            "do kiedy",
            "od kiedy",
            "w jakim terminie",
            "kiedy mozna",
            "kiedy trzeba",
            "kiedy nalezy",
            "do jakiego",
            "w jakim czasie",
            "ile dni",
        ],
    ),
    (
        "TAK_NIE",
        [
            "czy moge",
            "czy mozna",
            "czy wolno",
            "czy jest",
            "czy trzeba",
            "czy musze",
            "czy student moze",
            "czy da sie",
            "czy istnieje",
        ],
    ),
    (
        "SKUTEK",
        [
            "co grozi",
            "co sie stanie",
            "jakie konsekwencje",
            "co mi grozi",
            "co bedzie",
            "co jezeli",
            "co jak",
            "co jesli",
            "jakie sa skutki",
        ],
    ),
    (
        "PROCEDURA",
        [
            "jak",
            "w jaki sposob",
            "jak mozna",
            "jak sie",
            "jak zlozyc",
            "jak uzyskac",
            "jak wznowic",
            "jak oblicza",
            "jak liczyc",
        ],
    ),
    (
        "DEFINICJA",
        [
            "co to jest",
            "co to",
            "czym jest",
            "co oznacza",
            "co to znaczy",
            "definicja",
            "co rozumiemy",
        ],
    ),
]


def wykryj_intencje(pytanie: str) -> str:
    """Zwraca typ intencji dla pytania."""
    p = pytanie.lower()
    p = re.sub(
        r"[ąćęłńóśźż]",
        lambda m: {
            "ą": "a",
            "ć": "c",
            "ę": "e",
            "ł": "l",
            "ń": "n",
            "ó": "o",
            "ś": "s",
            "ź": "z",
            "ż": "z",
        }[m.group()],
        p,
    )

    for typ, wzorce in INTENCJE:
        if any(w in p for w in wzorce):
            return typ
    return "OGOLNE"


# ── ekstrakcja wartości z odpowiedzi ─────────────────────────────────────────

# liczby słownie → cyfry
LICZBY_SLOWNIE = {
    "raz": "1",
    "jeden": "1",
    "jedna": "1",
    "dwa razy": "2",
    "dwa": "2",
    "dwie": "2",
    "dwoch": "2",
    "dwukrotnie": "2",
    "dwukrotnego": "2",
    "dwukrotnego skladania": "2",
    "dwoch terminow": "2",
    "dwoch termin": "2",
    "trzy razy": "3",
    "trzy": "3",
    "trzech": "3",
    "trzykrotnie": "3",
    "trzecia realizacja": "3",
    "trzeciej realizacji": "3",
    "dopuszcza sie druga oraz trzecia": "3",
    "druga oraz trzecia": "3",
    "pieciodniowym": "5",
    "pięciodniowym": "5",
    "trzeciego dnia": "3",
    "druga oraz trzecia": "3",
    "drugą oraz trzecią": "3",
    "trzecia realizacja": "3",
    "trzecią realizację": "3",
    "cztery": "4",
    "czterech": "4",
    "piec": "5",
    "pięć": "5",
    "pieciu": "5",
    "szesc": "6",
    "sześć": "6",
    "siedem": "7",
    "osiem": "8",
    "dziewiec": "9",
    "dziesiec": "10",
    "pietnastu": "15",
    "piętnastu": "15",
    "trzynastu": "13",
    "trzynascie": "13",
}


def _usun_ogonki(tekst: str) -> str:
    return tekst.translate(str.maketrans("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ", "acelnoszzACELNOSZZ"))


def wyciagnij_liczbe(tekst: str) -> str | None:
    """Wyciąga pierwszą liczbę z tekstu (cyfra lub słownie)."""
    # krok 1 – oczyść tekst z numerów ustępów i porządkowych przed wszystkim innym
    tekst_czysty = re.sub(r"\bust\.?\s*\d+", "", tekst)
    tekst_czysty = re.sub(r"\bpkt\.?\s*\d+", "", tekst_czysty)
    tekst_czysty = re.sub(r"\bart\.?\s*\d+", "", tekst_czysty)
    tekst_czysty = re.sub(r"§\s*\d+", "", tekst_czysty)
    tekst_czysty = re.sub(
        r"\b(czwartego|czwarty|czwartej|czterech)\s+tygodni\w*", "", tekst_czysty
    )
    tekst_czysty = re.sub(
        r"\b(pierwszego|drugiego|trzeciego|czwartego|piątego|szóstego)\s+dnia\b",
        "",
        tekst_czysty,
    )
    tekst_czysty = re.sub(
        r"\b(pierwszego|drugiego|trzeciego|czwartego|piątego)\s+tygodnia\b",
        "",
        tekst_czysty,
    )

    # krok 2 – sprawdź słownik (bez ogonków żeby "trzecią"→"trzecia" pasowało)
    tekst_lower = _usun_ogonki(tekst_czysty.lower())
    for slowo, cyfra in LICZBY_SLOWNIE.items():
        # \b = granica słowa – "raz" nie trafia w "realizację"
        if re.search(r"\b" + re.escape(slowo) + r"\b", tekst_lower):
            return cyfra

    # krok 3 – cyfry które zostały po czyszczeniu
    m = re.search(r"\b([1-9]\d?)\b", tekst_czysty)
    if m:
        return m.group(1)

    return None


def wyciagnij_termin(tekst: str) -> str | None:
    """Wyciąga termin/datę z tekstu."""
    wzorce = [
        r"do\s+(\d+)\s+(stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|sierpnia|września|października|listopada|grudnia)",
        r"(\d+)\s+dni\s+robocz\w+",
        r"(\d+)\s+dni\s+kalendarzow\w+",
        r"w\s+ciągu\s+(\d+)\s+dni",
        r"nie\s+później\s+niż\s+(.{5,40}?)[\.,]",
        r"do\s+końca\s+(.{5,40}?)[\.,]",
        r"najpóźniej\s+do\s+(.{5,40}?)[\.,]",
        r"w\s+terminie\s+(.{5,40}?)[\.,]",
        r"(trzeciego\s+dnia\s+roboczego\s+.{5,40}?)[\.,]",
        r"co\s+najmniej\s+(\w+\s+dniow\w+\s+odstep\w*)",
        r"co\s+najmniej\s+(\w+\s+dniowym\s+odstep\w*)",
        r"pieciodniowym\s+odstep\w*",
        r"pięciodniowym\s+odstep\w*",
        r"co\s+najmniej\s+pięciodniowym\s+odstępem",
        r"co\s+najmniej\s+pieciodniowym\s+odstepem",
    ]
    # specjalny przypadek – "pięciodniowym odstępem" bez wzorca
    if re.search(r"pi[eę]ciodniow\w+\s+odst[eę]p\w*", tekst, re.IGNORECASE):
        return "co najmniej 5 dni"
    for wzorzec in wzorce:
        m = re.search(wzorzec, tekst, re.IGNORECASE)
        if m:
            return m.group(0).strip()
    return None


def generuj_skrot(intencja: str, pytanie: str, zdanie: str) -> str | None:
    """
    Generuje krótką, konkretną odpowiedź na podstawie intencji.
    Zwraca None jeśli nie udało się wyciągnąć wartości.

    Przykłady:
      LICZBA  + "ile razy egzamin" → "2 razy"
      TERMIN  + "kiedy sesja"      → "nie później niż 15 lipca"
      TAK_NIE + "czy mogę urlop"   → "Tak – masz do tego prawo"
    """
    if intencja == "LICZBA":
        liczba = wyciagnij_liczbe(zdanie)
        if liczba:
            p = pytanie.lower()
            if any(s in p for s in ["egzamin", "podejsc", "termin"]):
                return f"Możesz podejść **{liczba} razy**."
            if any(s in p for s in ["urlop", "semestr"]):
                return f"Maksymalnie **{liczba}** w całym toku studiów."
            if any(s in p for s in ["powtarzac", "przedmiot"]):
                return f"Możesz powtarzać **{liczba} razy** (na więcej potrzeba zgody Rektora)."
            if any(s in p for s in ["wznow"]):
                return f"Możesz wznowić studia maksymalnie **{liczba} razy**."
            return f"Odpowiedź: **{liczba}**."

    if intencja == "TERMIN":
        termin = wyciagnij_termin(zdanie)
        if termin:
            p = pytanie.lower()
            if "ile dni" in p:
                return f"Odstęp: **{termin}**."
            if "kiedy" in p:
                return f"**{termin}**."
            return f"Termin: **{termin}**."

    if intencja == "TAK_NIE":
        zdanie_lower = zdanie.lower()
        if any(
            s in zdanie_lower
            for s in [
                "nie może odmówić",
                "ma prawo",
                "może",
                "wolno",
                "jest uprawniony",
            ]
        ):
            return "**Tak** – masz do tego prawo."
        if any(
            s in zdanie_lower
            for s in ["nie może", "nie wolno", "zabronione", "niedopuszczalne"]
        ):
            return "**Nie** – regulamin tego zabrania."

    if intencja == "SKUTEK":
        if any(
            s in zdanie.lower()
            for s in [
                "skreśl",
                "niedostateczny",
                "niezaliczenie",
                "może stanowić podstawę",
            ]
        ):
            # wyciągnij konkretny skutek
            m = re.search(
                r"(podstawę\s+.{10,60}|skutkuje\s+.{10,60}|grozi\s+.{10,60})",
                zdanie,
                re.IGNORECASE,
            )
            if m:
                return f"Grozi: **{m.group(0).strip()}**."

    return None
