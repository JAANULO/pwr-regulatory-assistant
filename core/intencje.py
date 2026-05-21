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

import os
import sys

# W Pythonie 3.11+ tomllib jest częścią biblioteki standardowej
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        raise ImportError(
            "Dla wersji Pythona starszych niż 3.11 wymagana jest biblioteka 'tomli'."
        )

import re


# ── wczytywanie konfiguracji intencji ─────────────────────────────────────────

_cfg_full_cache: dict | None = None
_cfg_intencje_mtime: float = 0.0


def pobierz_pelna_konfiguracje() -> dict:
    global _cfg_full_cache, _cfg_intencje_mtime
    sciezka = os.path.join(
        os.path.dirname(__file__), "..", "data", "config", "intencje.toml"
    )
    if not os.path.exists(sciezka):
        sciezka = os.path.join("data", "config", "intencje.toml")

    if not os.path.exists(sciezka):
        raise FileNotFoundError(
            f"Krytyczny błąd: Plik konfiguracji intencji nie istnieje w lokalizacji: {os.path.abspath(sciezka)}"
        )

    try:
        mtime = os.path.getmtime(sciezka)
        if _cfg_full_cache is None or mtime > _cfg_intencje_mtime:
            with open(sciezka, "rb") as f:
                _cfg_full_cache = tomllib.load(f)
            _cfg_intencje_mtime = mtime
    except Exception as e:
        if _cfg_full_cache is None:
            raise RuntimeError(
                f"Krytyczny błąd podczas wczytywania konfiguracji intencji TOML ({sciezka}): {e}"
            )

    return _cfg_full_cache


def pobierz_konfiguracje_intencji() -> list[tuple[str, list[str]]]:
    cfg = pobierz_pelna_konfiguracje()
    intencje_dict = cfg.get("intencje", {})
    lista_intencji = []
    for typ, wzorce in intencje_dict.items():
        lista_intencji.append((typ, list(wzorce)))
    return lista_intencji


def wykryj_intencje(pytanie: str) -> str:
    """Zwraca typ intencji dla pytania."""
    p = pytanie.lower()
    cfg = pobierz_pelna_konfiguracje()
    mapa_diakrytyczne = cfg.get("diakrytyczne", {})
    if mapa_diakrytyczne:
        p = re.sub(
            r"[" + "".join(mapa_diakrytyczne.keys()) + "]",
            lambda m: mapa_diakrytyczne[m.group()],
            p,
        )

    intencje = pobierz_konfiguracje_intencji()
    for typ, wzorce in intencje:
        if any(w in p for w in wzorce):
            return typ
    return "OGOLNE"


# ── ekstrakcja wartości z odpowiedzi ─────────────────────────────────────────


def _usun_ogonki(tekst: str) -> str:
    cfg = pobierz_pelna_konfiguracje()
    mapa = cfg.get("diakrytyczne", {})
    if not mapa:
        return tekst.translate(
            str.maketrans("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ", "acelnoszzACELNOSZZ")
        )
    src = "".join(mapa.keys())
    dst = "".join(mapa.values())
    src += src.upper()
    dst += dst.upper()
    return tekst.translate(str.maketrans(src, dst))


def wyciagnij_liczbe(tekst: str) -> str | None:
    """Wyciąga pierwszą liczbę z tekstu (cyfra lub słownie)."""
    # krok 1 – oczyść tekst z numerów ustępów i porządkowych przed wszystkim innym
    tekst_czysty = re.sub(r"\bust\.?\s*\d+", "", tekst)
    tekst_czysty = re.sub(r"\bpkt\.?\s*\d+", "", tekst_czysty)
    tekst_czysty = re.sub(r"\bart\.?\s*\d+", "", tekst_czysty)
    tekst_czysty = re.sub(r"§\s*\d+", "", tekst_czysty)

    cfg = pobierz_pelna_konfiguracje()
    wzorce_czyszczenia = cfg.get("czyszczenie", {}).get("wzorce", [])
    for wzorzec in wzorce_czyszczenia:
        tekst_czysty = re.sub(wzorzec, "", tekst_czysty)

    # krok 2 – sprawdź słownik (bez ogonków żeby "trzecią"→"trzecia" pasowało)
    tekst_lower = _usun_ogonki(tekst_czysty.lower())
    liczby_slownie = cfg.get("liczby_slownie", {})
    for slowo, cyfra in liczby_slownie.items():
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
    cfg = pobierz_pelna_konfiguracje()
    terminy_cfg = cfg.get("terminy", {})
    wzorce = terminy_cfg.get("wzorce", [])
    specjalne = terminy_cfg.get("specjalne", {})

    specjalny_wzorzec = specjalne.get("wzorzec", r"pi[eę]ciodniow\w+\s+odst[eę]p\w*")
    specjalna_odpowiedz = specjalne.get("odpowiedz", "co najmniej 5 dni")

    if re.search(specjalny_wzorzec, tekst, re.IGNORECASE):
        return specjalna_odpowiedz
    for wzorzec in wzorce:
        m = re.search(wzorzec, tekst, re.IGNORECASE)
        if m:
            return m.group(0).strip()
    return None


def generuj_skrot(intencja: str, pytanie: str, zdanie: str) -> str | None:
    """
    Generuje krótką, konkretną odpowiedź na podstawie intencji.
    Zwraca None jeśli nie udało się wyciągnąć wartości.
    """
    cfg = pobierz_pelna_konfiguracje()
    klucze = cfg.get("skroty_klucze", {})
    szablony = cfg.get("szablony", {})

    if intencja == "LICZBA":
        liczba = wyciagnij_liczbe(zdanie)
        if liczba:
            p = pytanie.lower()
            szablony_liczba = szablony.get("liczba", {})
            if any(s in p for s in klucze.get("liczba_egzamin", [])):
                return szablony_liczba.get(
                    "egzamin", "Możesz podejść **{liczba} razy**."
                ).format(liczba=liczba)
            if any(s in p for s in klucze.get("liczba_urlop", [])):
                return szablony_liczba.get(
                    "urlop", "Maksymalnie **{liczba}** w całym toku studiów."
                ).format(liczba=liczba)
            if any(s in p for s in klucze.get("liczba_powtorz", [])):
                return szablony_liczba.get(
                    "powtorz",
                    "Możesz powtarzać **{liczba} razy** (na więcej potrzeba zgody Rektora).",
                ).format(liczba=liczba)
            if any(s in p for s in klucze.get("liczba_wznow", [])):
                return szablony_liczba.get(
                    "wznow", "Możesz wznowić studia maksymalnie **{liczba} razy**."
                ).format(liczba=liczba)
            return szablony_liczba.get("domyslny", "Odpowiedź: **{liczba}**.").format(
                liczba=liczba
            )

    if intencja == "TERMIN":
        termin = wyciagnij_termin(zdanie)
        if termin:
            p = pytanie.lower()
            szablony_termin = szablony.get("termin", {})
            if "ile dni" in p:
                return szablony_termin.get("ile_dni", "Odstęp: **{termin}**.").format(
                    termin=termin
                )
            if "kiedy" in p:
                return szablony_termin.get("kiedy", "**{termin}**.").format(
                    termin=termin
                )
            return szablony_termin.get("domyslny", "Termin: **{termin}**.").format(
                termin=termin
            )

    if intencja == "TAK_NIE":
        zdanie_lower = zdanie.lower()
        szablony_tak_nie = szablony.get("tak_nie", {})
        if any(s in zdanie_lower for s in klucze.get("tak_slowa", [])):
            return szablony_tak_nie.get("tak", "**Tak** – masz do tego prawo.")
        if any(s in zdanie_lower for s in klucze.get("nie_slowa", [])):
            return szablony_tak_nie.get("nie", "**Nie** – regulamin tego zabrania.")

    if intencja == "SKUTEK":
        if any(s in zdanie.lower() for s in klucze.get("skutek_slowa", [])):
            wzorzec_ekstrakcji = cfg.get("skutek_ekstrakcja", {}).get(
                "wzorzec", r"(podstawę\s+.{10,60}|skutkuje\s+.{10,60}|grozi\s+.{10,60})"
            )
            m = re.search(wzorzec_ekstrakcji, zdanie, re.IGNORECASE)
            if m:
                szablon_skutek = szablony.get("skutek", {}).get(
                    "domyslny", "Grozi: **{skutek}**."
                )
                return szablon_skutek.format(skutek=m.group(0).strip())

    return None
