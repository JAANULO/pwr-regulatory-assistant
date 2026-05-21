"""
formatowanie.py - przyjazne odpowiedzi na podstawie fragmentu regulaminu
"""

import os
import random
import re
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

from .wyszukiwarka import tokenizuj as _tokenizuj

if __name__ != "__main__":
    from domain.models import WynikWyszukiwania
else:
    # Dla testów lokalnych
    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from domain.models import WynikWyszukiwania


# ── wczytywanie konfiguracji formatowania ─────────────────────────────────────

_cfg_formatowanie_cache: dict | None = None
_cfg_formatowanie_mtime: float = 0.0


def pobierz_konfiguracje_formatowania() -> dict:
    global _cfg_formatowanie_cache, _cfg_formatowanie_mtime
    sciezka = os.path.join(
        os.path.dirname(__file__), "..", "data", "config", "formatowanie.toml"
    )
    if not os.path.exists(sciezka):
        sciezka = os.path.join("data", "config", "formatowanie.toml")

    if not os.path.exists(sciezka):
        raise FileNotFoundError(
            f"Krytyczny błąd: Plik konfiguracji formatowania nie istnieje w lokalizacji: {os.path.abspath(sciezka)}"
        )

    try:
        mtime = os.path.getmtime(sciezka)
        if _cfg_formatowanie_cache is None or mtime > _cfg_formatowanie_mtime:
            with open(sciezka, "rb") as f:
                _cfg_formatowanie_cache = tomllib.load(f)
            _cfg_formatowanie_mtime = mtime
    except Exception as e:
        if _cfg_formatowanie_cache is None:
            raise RuntimeError(
                f"Krytyczny błąd podczas wczytywania konfiguracji formatowania TOML ({sciezka}): {e}"
            )

    return _cfg_formatowanie_cache


# ── funkcje pomocnicze ────────────────────────────────────────────────────────


def wykryj_temat(pytanie: str) -> str:
    """wykrywa temat pytania na podstawie słów kluczowych"""
    pytanie_lower = pytanie.lower()
    cfg = pobierz_konfiguracje_formatowania()
    tematy = cfg.get("tematy", {})
    for temat, slowa in tematy.items():
        if any(s in pytanie_lower for s in slowa):
            return temat
    return "domyślny"


def _score_zdanie(zdanie: str, tokeny_pytania: list[str]) -> int:
    """Liczy ile tokenów pytania pojawia się w zdaniu – im więcej, tym lepiej."""
    zdanie_lower = zdanie.lower()
    return sum(1 for t in tokeny_pytania if t in zdanie_lower)


def wyciagnij_zdania(
    tresc: str,
    max_zdan: int = 3,
    szukaj: list[str] | None = None,
    pytanie_tokeny: list[str] | None = None,
) -> list[str]:
    tresc = re.sub(r"^§\s*\d+\.\s*\S[^\n\.]{0,60}\.?\s*", "", tresc).strip()
    tresc_split = re.sub(
        r"(?<!\bust)(?<!\bpkt)(?<!\bart)(?<!\bpoz)(?<!\bm\.in)\.\s+(?=[A-ZŁŚŻŹ\d])",
        "|||",
        tresc,
    )
    czesci = [c.strip() for c in tresc_split.split("|||") if len(c.strip()) > 30]

    oczyszczone = []
    for z in czesci:
        z = re.sub(r"\s*Rozdział\s+[IVX]+[^.]*\.?", "", z)
        z = z.strip().rstrip(".,;: ")
        z = re.sub(r"\([^)]{0,80}\)", "", z).strip()
        z = re.sub(r"\s+\d+$", "", z).strip()
        z = re.sub(r"\s+", " ", z)
        if len(z) > 30:
            oczyszczone.append(z)

    # sortuj zdania po dopasowaniu do pytania – najlepsze na górę
    if pytanie_tokeny:
        oczyszczone.sort(key=lambda z: _score_zdanie(z, pytanie_tokeny), reverse=True)
    elif szukaj:
        oczyszczone.sort(
            key=lambda z: sum(1 for s in szukaj if s in z.lower()), reverse=True
        )

    wynik = []
    for z in oczyszczone[:max_zdan]:
        # pokaż całe zdanie – urwane zdanie jest gorsze niż długie
        wynik.append(z)

    return wynik


def wyciagnij_skale_ocen(tresc: str) -> str:
    """specjalna obsługa – wyciąga tabelę ocen jako czytelne punkty"""
    cfg = pobierz_konfiguracje_formatowania()
    skala_cfg = cfg.get("skala_ocen", {})
    naglowek = skala_cfg.get("naglowek")
    oceny = skala_cfg.get("oceny")

    if not naglowek or not oceny:
        raise KeyError("Brak prawidłowej konfiguracji 'skala_ocen' w pliku TOML")

    linie = [naglowek]
    linie.append("  " + "─" * 38)
    for cyfra, slowo, prog in oceny:
        linie.append(f"  {cyfra:<8} {slowo:<22} {prog}")
    return "\n".join(linie)


# ── główna funkcja ────────────────────────────────────────────────────────────


def formatuj_odpowiedz(
    pytanie: str,
    wynik_wyszukiwarki: "WynikWyszukiwania | None",
    najlepsze_zdanie: str | None = None,
    skrot: str | None = None,
    tylko_jedno: bool = False,
) -> dict | str:
    """
    tworzy przyjazną odpowiedź na podstawie pytania i wyniku z wyszukiwarki.

    przykład wyjścia:
      📝 W sprawie egzaminów regulamin mówi:
        • Masz prawo do dwóch terminów egzaminu
        • Drugi termin musi być co najmniej 5 dni po pierwszym

      📖 Źródło: § 18. Egzaminy
      💡 Jeśli masz dodatkowe pytania – pytaj!
    """
    cfg_format = pobierz_konfiguracje_formatowania()
    szablony = cfg_format.get("szablony", {})

    if not wynik_wyszukiwarki:
        if "brak_wynikow" not in szablony:
            raise KeyError("Brak konfiguracji 'brak_wynikow' w sekcji [szablony]")
        return szablony["brak_wynikow"]

    tytul = wynik_wyszukiwarki.tytul
    tresc = wynik_wyszukiwarki.tresc
    podobienstwo = wynik_wyszukiwarki.podobienstwo

    # za niskie dopasowanie
    if podobienstwo < 0.08:
        if "niskie_dopasowanie" not in szablony:
            raise KeyError("Brak konfiguracji 'niskie_dopasowanie' w sekcji [szablony]")
        return szablony["niskie_dopasowanie"].format(tytul=tytul)

    # dobierz wstęp: najpierw po pytaniu, potem skoryguj po faktycznym tytule paragrafu
    wstepy = cfg_format.get("wstepy", {})

    temat = wykryj_temat(pytanie)
    wstep = wstepy.get(temat, wstepy.get("domyślny", ""))

    tytul_lower = tytul.lower()
    wstepy_specjalne = cfg_format.get("wstepy_specjalne", {})
    wstepy_dopasowanie = cfg_format.get("wstepy_specjalne_dopasowanie", {})

    for klucz, frazy in wstepy_dopasowanie.items():
        if any(f in tytul_lower for f in frazy):
            wstep = wstepy_specjalne.get(klucz, wstep)
            break

    # wyciągnij kluczowe zdania i sformatuj jako punkty
    # zdania = wyciagnij_zdania(tresc, max_zdan=3)

    slowa_kluczowe = cfg_format.get("slowa_kluczowe", {})

    tokeny_pyt = _tokenizuj(pytanie)

    jest_skala = False
    wstepy_dopasowanie = cfg_format.get("wstepy_specjalne_dopasowanie", {})
    for f in wstepy_dopasowanie.get("skala_ocen", []):
        if f in tytul.lower():
            jest_skala = True
            break

    if jest_skala:
        zdania = [wyciagnij_skale_ocen(tresc)]
    else:
        slowa = None
        for fraza, kluczowe in slowa_kluczowe.items():
            if fraza in pytanie.lower():
                slowa = kluczowe
                break
        zdania = wyciagnij_zdania(
            tresc, max_zdan=3, szukaj=slowa, pytanie_tokeny=tokeny_pyt
        )

    zachety = cfg_format.get("zachety", [])
    zacheta = random.choice(zachety) if podobienstwo > 0.2 and zachety else None  # nosec B311

    # Pokaż "pełny paragraf" tylko jeśli punkty to < 40% treści
    # Logika wyświetlania pełnego paragrafu jest realizowana na froncie

    if najlepsze_zdanie and najlepsze_zdanie not in (zdania or []):
        if tylko_jedno:
            punkty = [najlepsze_zdanie]
        else:
            drugie = None
            if zdania:
                tokeny_pyt = pytanie.lower().split()
                for z in zdania:
                    if (
                        z != najlepsze_zdanie
                        and sum(1 for t in tokeny_pyt if t in z.lower()) >= 2
                    ):
                        drugie = z
                        break
            punkty = [najlepsze_zdanie] + ([drugie] if drugie else [])
    else:
        punkty = (
            zdania[:1] if tylko_jedno else (zdania[:2] if zdania else [tresc[:200]])
        )

    return {
        "wstep": skrot if skrot else wstep.strip(),
        "punkty": [] if skrot else punkty,
        "tytul": tytul,
        "zacheta": zacheta,
        "podobienstwo": podobienstwo,
        "pelna_tresc": tresc,
        "najlepsze_zdanie": najlepsze_zdanie
        if najlepsze_zdanie
        else (punkty[0] if punkty else None),
    }


# ── test ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.join(BASE_DIR, ".."))
    from infrastructure.knowledge_loader import utworz_wyszukiwarke  # type: ignore

    w = utworz_wyszukiwarke(os.path.join(BASE_DIR, "..", "data", "baza_wiedzy.json"))

    pytania = [
        "co mam zrobić jak nie zdam egzaminu",
        "ile razy mozna powtarzac egzamin",
        "kiedy mozna wziac urlop dziekanski",
        "jak oblicza sie srednia ocen",
        "co grozi za nieobecnosci",
        "kiedy mozna zostac skreslanym z listy",
        "jak wyglada praca dyplomowa",
        "ile osob moze pisac wspolna prace",
    ]

    for pytanie in pytania:
        wyniki = w.szukaj(pytanie, n_wynikow=1)
        wynik = wyniki[0] if wyniki else None
        odp = formatuj_odpowiedz(pytanie, wynik)
        print(f"{'=' * 55}")
        print(f"❓ {pytanie}")
        print(f"{'─' * 55}")
        print(odp)
        print()
