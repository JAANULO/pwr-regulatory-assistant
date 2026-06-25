"""
wyszukiwarka.py - Krok 2 wersji 2.0
Algorytm TF-IDF napisany od zera.
Wyszukuje w bazie wiedzy fragment najbardziej pasujacy do pytania.
"""

import math
import os
import re
import time
import tomllib
from collections import Counter
from typing import Any

_config_cache: dict[str, Any] | None = None
_config_mtime: float = 0.0


def pobierz_konfiguracje() -> dict[str, Any]:
    global _config_cache, _config_mtime
    sciezka = os.path.join(
        os.path.dirname(__file__), "..", "data", "config", "config.toml"
    )
    if not os.path.exists(sciezka):
        sciezka = os.path.join("data", "config", "config.toml")

    if not os.path.exists(sciezka):
        sciezka_example = os.path.join(
            os.path.dirname(__file__), "..", "data", "config", "config.example.toml"
        )
        if os.path.exists(sciezka_example):
            sciezka = sciezka_example
        else:
            sciezka_example_alt = os.path.join("data", "config", "config.example.toml")
            if os.path.exists(sciezka_example_alt):
                sciezka = sciezka_example_alt

    if os.path.exists(sciezka):
        try:
            mtime = os.path.getmtime(sciezka)
            if _config_cache is None or mtime > _config_mtime:
                with open(sciezka, "rb") as f:
                    _config_cache = tomllib.load(f)
                _config_mtime = mtime
        except Exception:  # nosec B110
            pass

    if _config_cache is None:
        _config_cache = {
            "bm25": {"k1": 1.5, "b": 0.75, "synonimy_waga": 0.85},
            "term_boosts": {},
            "mapa_wag_statyczna": {},
            "mapa_wag_dynamiczna": {},
            "nlp": {"prog_dlugosci_slowa_korekcja": 8, "tytul_mnoznik": 3},
            "wyszukiwanie_wielozdaniowe": {"waga_pobocznych_zdan": 0.25},
            "slownik_pojec": {"min_dlugosc_korekty": 4, "max_dystans_levenshteina": 1},
        }
    return _config_cache


try:
    from core.bd import pobierz_wspolczynniki_zbiorczo
    from core.slowniki import ROZSZERZENIA, SYNONIMY
    from domain.models import WynikWyszukiwania
except ImportError:
    from .bd import pobierz_wspolczynniki_zbiorczo
    from .slowniki import ROZSZERZENIA, SYNONIMY
    from ..domain.models import WynikWyszukiwania  # type: ignore

PLIK_BAZY = os.path.join(
    os.path.dirname(__file__), "..", "data", "kb", "baza_wiedzy.json"
)
MAPA_WAG_TTL = 60
_mapa_wag_cache: dict[str, Any] = {"ts": 0.0, "data": {}}


def _pobierz_mapa_wag_cached() -> dict[str, float]:
    obecny_czas = time.time()
    if obecny_czas - _mapa_wag_cache["ts"] <= MAPA_WAG_TTL:
        return _mapa_wag_cache["data"]  # type: ignore

    _mapa_wag_cache["data"] = pobierz_wspolczynniki_zbiorczo()
    _mapa_wag_cache["ts"] = obecny_czas
    return _mapa_wag_cache["data"]  # type: ignore


# ── Krok 1: przygotowanie tekstu ──────────────────────────────────────────────

MAPA_ZNAKOW = str.maketrans("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ", "acelnoszzACELNOSZZ")


def usun_polskie_znaki(tekst: str) -> str:
    """zamienia polskie litery na odpowiedniki bez ogonkow"""
    return tekst.translate(MAPA_ZNAKOW)


def levenshtein(a: str, b: str) -> int:
    """oblicza odległość edycyjną między dwoma słowami"""
    if len(a) < len(b):
        return levenshtein(b, a)
    if not b:
        return len(a)
    poprzedni = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        aktualny = [i + 1]
        for j, cb in enumerate(b):
            wstaw = poprzedni[j + 1] + 1
            usun = aktualny[j] + 1
            zamien = poprzedni[j] + (ca != cb)
            aktualny.append(min(wstaw, usun, zamien))
        poprzedni = aktualny
    return poprzedni[-1]


# Cache korekcji literówek – raz obliczone, zapamiętane na całą sesję
_cache_literowek: dict[str, str] = {}
_cache_mapy_fonetycznej: dict[int, dict[str, str]] = {}


def uprosc_fonetycznie(slowo: str) -> str:
    """
    Upraszcza słowo fonetycznie do porównań tolerancyjnych dla błędów ortograficznych w j. polskim.
    Obsługuje ch->h, rz->z, sz->s, cz->c, o->u, i->y, j->y.
    """
    # Najpierw usuwamy polskie znaki dla ujednolicenia (np. ó -> o, ż -> z)
    slowo = usun_polskie_znaki(slowo.lower())
    slowo = slowo.replace("ch", "h")
    slowo = slowo.replace("rz", "z")
    slowo = slowo.replace("sz", "s")
    slowo = slowo.replace("cz", "c")
    slowo = slowo.replace("o", "u")
    slowo = slowo.replace("i", "y")
    slowo = slowo.replace("j", "y")
    return slowo


def _pobierz_mape_fonetyczna(slownik: set[str] | dict[str, float]) -> dict[str, str]:
    """Generuje i cache'uje mapę uproszczeń fonetycznych dla słownika."""
    slownik_id = id(slownik)
    if slownik_id in _cache_mapy_fonetycznej:
        return _cache_mapy_fonetycznej[slownik_id]

    mapa = {}
    for s in slownik:
        uf = uprosc_fonetycznie(s)
        # Zachowujemy oryginalne słowo dla danej formy fonetycznej
        if uf not in mapa:
            mapa[uf] = s
    _cache_mapy_fonetycznej[slownik_id] = mapa
    return mapa


def popraw_literowke(
    slowo: str, slownik: set[str] | dict[str, float], max_odleglosc: int = 1
) -> str:
    """
    Koryguje literówki z uwzględnieniem fonetyki języka polskiego.
    Używa szybkiej ścieżki O(1) dla dokładnych dopasowań homofonicznych,
    a dla pozostałych liczy dystans Levenshteina na uproszczonych formach fonetycznych.
    """
    if slowo in slownik:
        return slowo
    if slowo in _cache_literowek:
        return _cache_literowek[slowo]

    # 1. Szybka ścieżka O(1): dokładne dopasowanie fonetyczne
    mapa_fonetyczna = _pobierz_mape_fonetyczna(slownik)
    slowo_fonetycznie = uprosc_fonetycznie(slowo)
    if slowo_fonetycznie in mapa_fonetyczna:
        poprawione = mapa_fonetyczna[slowo_fonetycznie]
        _cache_literowek[slowo] = poprawione
        return poprawione

    # 2. Ścieżka Levenshteina: fuzzy matching na formach fonetycznych
    # Dla dłuższych słów pozwalamy na większy błąd
    cfg = pobierz_konfiguracje()
    prog_dlugosci = cfg.get("nlp", {}).get("prog_dlugosci_slowa_korekcja", 8)
    aktualna_odleglosc = 2 if len(slowo) > prog_dlugosci else max_odleglosc

    # Filtrujemy kandydatów po pierwszej literze fonetycznej oraz długości
    kandydaci = [
        s
        for s in slownik
        if abs(len(s) - len(slowo)) <= aktualna_odleglosc
        and uprosc_fonetycznie(s)[0] == slowo_fonetycznie[0]
    ]

    najlepszy = None
    najlepsza_odleglosc = aktualna_odleglosc + 1

    for k in kandydaci:
        k_fonetycznie = uprosc_fonetycznie(k)
        odl = levenshtein(slowo_fonetycznie, k_fonetycznie)
        if odl < najlepsza_odleglosc:
            najlepsza_odleglosc = odl
            najlepszy = k

    wynik = (
        najlepszy
        if (najlepszy and najlepsza_odleglosc <= aktualna_odleglosc)
        else slowo
    )
    _cache_literowek[slowo] = wynik
    return wynik


def normalizuj(slowo: str) -> str:
    """zamienia odmianę słowa na formę podstawową używając słownika synonimów"""
    return SYNONIMY.get(slowo, slowo)


_STOPWORDS_CACHE: set[str] | None = None


def pobierz_stopwords() -> set[str]:
    global _STOPWORDS_CACHE
    if _STOPWORDS_CACHE is None:
        cfg = pobierz_konfiguracje()
        stopwords_list = cfg.get("szumy_i_wykluczenia", {}).get(
            "stopwords",
            [
                "i",
                "w",
                "z",
                "do",
                "na",
                "ze",
                "nie",
                "sie",
                "jest",
                "to",
                "a",
                "o",
                "lub",
                "oraz",
                "po",
                "przez",
                "przy",
                "ten",
                "ta",
                "te",
                "tego",
                "tej",
                "tym",
                "tych",
                "od",
                "za",
                "jak",
                "czy",
                "co",
                "kt",
                "kto",
                "ale",
                "bo",
                "by",
                "go",
                "mu",
                "jej",
                "ich",
                "im",
                "je",
                "dla",
                "gdy",
                "az",
                "tez",
                "juz",
                "jesli",
                "jego",
                "jako",
                "ocen",
                "prawdziwe",
                "zdanie",
                "prawda",
                "falsz",
            ],
        )
        _STOPWORDS_CACHE = set(stopwords_list)
    return _STOPWORDS_CACHE


def tokenizuj(tekst: str, slownik_korekcji: set[str] | None = None) -> list[str]:
    """
    rozbija tekst na liste slow (tokenow).
    usuwa interpunkcje, zamienia na male litery,
    normalizuje polskie znaki zeby pytania bez ogonkow tez dzialaly.
    """
    tekst = tekst.lower()
    tekst = usun_polskie_znaki(tekst)
    tekst = re.sub(r"[^\w\s]", " ", tekst)

    slowa = tekst.split()
    # 1. Filtrujemy stopwords i krótkie tokeny najpierw
    filtrowane = [
        s for s in slowa if s not in pobierz_stopwords() and (len(s) > 1 or s.isdigit())
    ]

    wyniki = []
    for s in filtrowane:
        # 2. Korygujemy literówki
        if slownik_korekcji:
            s = popraw_literowke(s, slownik_korekcji)
        # 3. Normalizujemy synonimami
        s = normalizuj(s)
        wyniki.append(s)

    return wyniki


# ── Krok 2: budowanie macierzy TF-IDF ────────────────────────────────────────


def oblicz_tf(slowa: list[str]) -> dict[str, float]:
    """
    oblicza czestotliwosc kazdego slowa we fragmencie.
    wynik: slownik {slowo: wartosc_tf}
    """
    licznik: dict[str, int] = {}
    for slowo in slowa:
        licznik[slowo] = licznik.get(slowo, 0) + 1

    tf = {}
    for slowo, liczba in licznik.items():
        tf[slowo] = liczba / len(slowa)
    return tf


# ── BM25 (zastępuje TF-IDF) ───────────────────────────────────────────────────
# k1 = nasycenie: jak szybko kolejne wystąpienia słowa przestają podbijać wynik
# b  = normalizacja: jak bardzo długość dokumentu wpływa na wynik
# wartości standardowe z literatury — działają dobrze dla większości zbiorów
BM25_K1 = 1.5
BM25_B = 0.75


def oblicz_idf_bm25(wszystkie_tokeny: list[list[str]]) -> dict[str, float]:
    """
    IDF w wersji BM25 — wzór Robertson/Sparck-Jones.
    Różnica vs klasyczne IDF: log((N - df + 0.5) / (df + 0.5))
    Słowa w ponad połowie dokumentów mogą dostać wynik ujemny (są za pospolite).
    """
    n = len(wszystkie_tokeny)
    idf = {}

    wszystkie_slowa = set()
    for tokeny in wszystkie_tokeny:
        wszystkie_slowa.update(tokeny)

    for slowo in wszystkie_slowa:
        df = sum(1 for tokeny in wszystkie_tokeny if slowo in tokeny)
        idf[slowo] = math.log((n - df + 0.5) / (df + 0.5) + 1)

    return idf


def zbuduj_wektory_bm25(
    wszystkie_tokeny: list[list[str]],
    idf: dict[str, float],
    custom_k1: float | None = None,
    custom_b: float | None = None,
) -> list[dict[str, float]]:
    """
    Buduje wektory BM25. Obsługa wirtualnego override dla Laboratorium (Tryb Symulacji).
    Kluczowa różnica: tf jest normalizowane przez długość dokumentu.
    Wzór: idf * (tf * (k1+1)) / (tf + k1 * (1 - b + b * dl/avgdl))
    """
    cfg = pobierz_konfiguracje()
    k1 = custom_k1 if custom_k1 is not None else cfg["bm25"].get("k1", 1.5)
    b = custom_b if custom_b is not None else cfg["bm25"].get("b", 0.75)
    avgdl = sum(len(t) for t in wszystkie_tokeny) / max(len(wszystkie_tokeny), 1)

    wektory = []
    for tokeny in wszystkie_tokeny:
        dl = len(tokeny)
        licznik: dict[str, int] = {}
        for slowo in tokeny:
            licznik[slowo] = licznik.get(slowo, 0) + 1

        wektor = {}
        for slowo, tf in licznik.items():
            idf_val = idf.get(slowo, 0)
            licznik_bm25 = tf * (k1 + 1)
            mianownik_bm25 = tf + k1 * (1 - b + b * dl / avgdl)
            wektor[slowo] = idf_val * (licznik_bm25 / mianownik_bm25)

        wektory.append(wektor)

    return wektory


# ── Krok 3: podobienstwo cosinusowe ──────────────────────────────────────────


def podobienstwo_cosinusowe(
    wektor_a: dict[str, float], wektor_b: dict[str, float]
) -> float:
    """
    mierzy jak bardzo dwa wektory sa do siebie podobne.
    wynik od 0 (brak podobienstwa) do 1 (identyczne).

    wzor: cos(theta) = (A . B) / (|A| * |B|)
    """
    # iloczyn skalarny - suma iloczynow wspolnych slow
    iloczyn = sum(
        wartosc * wektor_b[slowo]
        for slowo, wartosc in wektor_a.items()
        if slowo in wektor_b
    )
    dlugosc_a = math.sqrt(sum(v**2 for v in wektor_a.values()))
    dlugosc_b = math.sqrt(sum(v**2 for v in wektor_b.values()))

    if dlugosc_a == 0 or dlugosc_b == 0:
        return 0.0

    return iloczyn / (dlugosc_a * dlugosc_b)


def podziel_pytanie_na_zdania(pytanie: str) -> list[str]:
    """
    Dzieli pytanie użytkownika na pojedyncze zdania (Query Segmentation).
    Zabezpiecza przed fałszywym podziałem na skrótach z kropką (np., tzw., tzn., itp., itd.).
    """
    # Popularne skróty w języku polskim
    skroty = r"\b(np|tzw|tzn|itp|itd|art|ust|pkt|r|poz|prof|dr)\."

    # Zamiana kropki po skrótach na tymczasowy marker
    tekst = re.sub(
        skroty, lambda m: m.group(1) + "TEMPdot", pytanie, flags=re.IGNORECASE
    )

    # Dzielimy po kropce, pytajniku lub wykrzykniku, po których następuje spacja lub koniec tekstu
    podzielone = re.split(r"[.?!]\s*(?=[A-ZŁŚŻŹa-złśżź]|$)", tekst)

    zdania = []
    for z in podzielone:
        z_czyste = z.replace("TEMPdot", ".").strip()
        if z_czyste:
            zdania.append(z_czyste)
    return zdania


def czy_zdanie_to_szum(zdanie: str) -> bool:
    """
    Sprawdza, czy zdanie jest szumem grzecznościowym lub potocznym zwrotem bez wartości kluczowych.
    """
    zdanie_norm = usun_polskie_znaki(zdanie.lower().strip().rstrip("?!."))

    cfg = pobierz_konfiguracje()
    szumy = set(cfg.get("szumy_i_wykluczenia", {}).get("szumy", []))

    if zdanie_norm in szumy:
        return True

    # Krótkie zdania o małej wartości bez unikalnych słów
    tokeny = tokenizuj(zdanie)
    if len(tokeny) <= 2:
        return True

    return False


# ── Glowna klasa wyszukiwarki ─────────────────────────────────────────────────


class Wyszukiwarka:
    def __init__(
        self,
        fragmenty: list[dict],
        idf: dict[str, float],
        wektory: list[dict[str, float]],
        wszystkie_tokeny: list[list[str]],
    ):
        self.fragmenty = fragmenty
        self.idf = idf
        self.wektory = wektory
        self.wszystkie_tokeny = wszystkie_tokeny

    @staticmethod
    def wykryj_numer_paragrafu(pytanie: str) -> str | None:
        """Wykrywa numer paragrafu z zapytania (np. §18, paragraf 18)."""
        # Standaryzacja: usuwamy polskie znaki i zamieniamy na małe litery
        p = usun_polskie_znaki(pytanie.lower())
        dopasowanie = re.search(r"(?:§\s*|paragraf(?:ie|u|em|owi|ach)?\s+)(\d+)", p)
        return dopasowanie.group(1) if dopasowanie else None

    def generuj_graf_slow(self, top_k: int = 70) -> dict:
        """Mapuje całą rozpiętość merytoryczną dokumentu w pary skojarzeń na podstawie sąsiedztwa."""

        # Cache na poziomie instancji - graf generujemy ZAWSZE TYLKO RAZ!
        cache_key = f"_graf_cache_{top_k}_dziala"
        if hasattr(self, cache_key):
            return getattr(self, cache_key)  # type: ignore

        bigramy: Counter[tuple[str, str]] = Counter()
        wystapienia_wezlow: Counter[str] = Counter()

        # Mielenie całych akapitów wyraz po wyrazie
        for tokeny in self.wszystkie_tokeny:
            for i in range(len(tokeny) - 1):
                A, B = tokeny[i], tokeny[i + 1]
                if len(A) < 3 or len(B) < 3:
                    continue  # śmieci i przyimki
                if A == B:
                    continue  # Zabezpieczenie przed pętlami własnymi (autorelacja tokenu)
                # Sortowanie, żeby kolejność słów (A->B czy B->A) nie grała roli
                para = tuple(sorted([A, B]))
                bigramy[para] += 1  # type: ignore

        najczestsze = bigramy.most_common(top_k)

        wezly_set: set[str] = set()
        edges = []
        for (A, B), waga in najczestsze:
            if waga < 2:
                continue  # Odrzucamy przypadek pojedynczy asocjacji
            wystapienia_wezlow[A] += waga
            wystapienia_wezlow[B] += waga
            wezly_set.add(A)
            wezly_set.add(B)
            edges.append(
                {
                    "from": A,
                    "to": B,
                    "value": waga,
                    "color": {"color": "rgba(200,200,200,0.3)", "highlight": "#ff3b30"},
                }
            )

        nodes = []
        for wezel in wezly_set:
            # Skalowanie rozmiaru węzła na podstawie stopnia węzła (node degree)
            wielkosc = 10 + min(wystapienia_wezlow[wezel] * 1.5, 40)
            nodes.append(
                {
                    "id": wezel,
                    "label": wezel,
                    "shape": "dot",
                    "size": wielkosc,
                    "color": "#007aff",
                    "font": {"color": "#888", "size": max(10, min(14, wielkosc))},
                }
            )

        wynik = {"nodes": nodes, "edges": edges}

        setattr(self, cache_key, wynik)
        return wynik

    def pobierz_paragraf_po_numerze(self, numer) -> "WynikWyszukiwania | None":
        """Zwraca fragment paragrafu po numerze lub None, bez liczenia BM25."""
        numer = str(numer)
        for frag in self.fragmenty:
            liczby_w_tytule = re.findall(r"\d+", frag["tytul"])
            if liczby_w_tytule and liczby_w_tytule[0] == numer:
                return WynikWyszukiwania(
                    tytul=frag["tytul"],
                    tresc=frag["tresc"],
                    podobienstwo=1.0,
                    zrodlo=frag.get("zrodlo"),
                )
        return None

    def generuj_graf_paragrafow(self) -> dict:
        """Generuje siatkę relacji między paragrafami na podstawie podobieństwa wektorowego."""
        cache_key = "_graf_paragrafow_cache"
        if hasattr(self, cache_key):
            return getattr(self, cache_key)  # type: ignore

        nodes = []
        for frag in self.fragmenty:
            etykieta = frag["tytul"][:35].rstrip() + (
                "..." if len(frag["tytul"]) > 35 else ""
            )
            nodes.append(
                {
                    "id": frag["tytul"],
                    "label": etykieta,
                    "shape": "dot",
                    "size": 18,
                    "color": "#007aff",
                    "font": {"color": "#aaa", "size": 11},
                }
            )

        edges = []
        for i in range(len(self.wektory)):
            for j in range(i + 1, len(self.wektory)):
                pod = podobienstwo_cosinusowe(self.wektory[i], self.wektory[j])
                if pod > 0.15:
                    edges.append(
                        {
                            "from": self.fragmenty[i]["tytul"],
                            "to": self.fragmenty[j]["tytul"],
                            "value": round(pod, 3),
                            "color": {
                                "color": "rgba(200,255,0,0.3)",
                                "highlight": "#c8ff00",
                            },
                        }
                    )

        wynik = {"nodes": nodes, "edges": edges}
        setattr(self, cache_key, wynik)
        return wynik

    def _szukaj_z_gotowymi_wektorami(
        self,
        pytanie: str,
        wektory_bazy: list[dict[str, float]],
        synonimy_waga: float,
        n_wynikow: int = 1,
        zrodlo: str | None = None,
        virtual_params: dict | None = None,
        cfg: dict | None = None,
    ) -> list[WynikWyszukiwania]:
        # Szybka ścieżka: zapytanie o konkretny paragraf bez BM25 (wyłączenie w locie labu z faktu na 1.0)
        numer_paragrafu = self.wykryj_numer_paragrafu(pytanie)
        if numer_paragrafu:
            trafienie = self.pobierz_paragraf_po_numerze(numer_paragrafu)
            if trafienie:
                return [trafienie]

        # Szybka ścieżka dla definicji ze słownika pojęć (§ 2)
        from core.szybkie_odpowiedzi import dopasuj_szybka_odpowiedz

        if cfg is None:
            cfg = pobierz_konfiguracje()

        # Wykluczamy pojęcia, które w bazie regresyjnej mają przypisane inne, bardziej szczegółowe paragrafy
        wykluczenia_cfg = cfg.get("szumy_i_wykluczenia", {})
        wykluczenia_szybkiej = set(
            wykluczenia_cfg.get("wykluczenia_szybkiej_sciezki", [])
        )

        pyt_norm = usun_polskie_znaki(pytanie.lower().strip().rstrip("?!"))
        czy_wykluczone = any(wykl in pyt_norm for wykl in wykluczenia_szybkiej)

        # Wyjątek: 'co to sa punkty ects' ma pasować do Słownika, ale 'co to jest punkt ects' do punktów ECTS
        fraza_ects = wykluczenia_cfg.get("fraza_wyjatku_ects", "punkty ects")
        fraza_ects_pomoc = wykluczenia_cfg.get("fraza_wyjatku_ects_pomoc", "sa")
        if fraza_ects in pyt_norm and fraza_ects_pomoc in pyt_norm:
            czy_wykluczone = False

        if not czy_wykluczone and dopasuj_szybka_odpowiedz(pytanie):
            trafienie = self.pobierz_paragraf_po_numerze(2)
            if trafienie:
                return [trafienie]

        # Segmentacja zapytania na zdania
        surowe_zdania = podziel_pytanie_na_zdania(pytanie)
        aktywne_zdania = [z for z in surowe_zdania if not czy_zdanie_to_szum(z)]

        # Jeśli brak aktywnych zdań po filtracji, cofamy się do pełnego pytania
        if not aktywne_zdania:
            aktywne_zdania = [pytanie]

        slownik_korekcji = set(self.idf.keys()) | set(SYNONIMY.keys())
        wszystkie_tokeny_pytania = []
        for zdanie in aktywne_zdania:
            tokeny_z = tokenizuj(zdanie, slownik_korekcji)
            rozszerzenie = []
            for tok in tokeny_z:
                if tok in ROZSZERZENIA:
                    rozszerzenie.extend(tokenizuj(ROZSZERZENIA[tok]))
            zdanie_lower = usun_polskie_znaki(zdanie.lower())
            for fraza, rozszerzenie_frazy in ROZSZERZENIA.items():
                if " " in fraza and fraza in zdanie_lower:
                    rozszerzenie.extend(tokenizuj(rozszerzenie_frazy))
            wszystkie_tokeny_pytania.extend(tokeny_z + rozszerzenie)
        wszystkie_tokeny_pytania_set = set(wszystkie_tokeny_pytania)

        mapa_wag_stat = cfg.get("mapa_wag_statyczna", {})
        mapa_wag_dyn = cfg.get("mapa_wag_dynamiczna", {})

        db_wag = _pobierz_mapa_wag_cached()
        mapa_wag = {}
        for f in self.fragmenty:
            tytul = f["tytul"]
            v = db_wag.get(tytul, 1.0)

            # 1. Statyczne wagi rozdziałów
            for klucz, mnoznik in mapa_wag_stat.items():
                if klucz in tytul:
                    v *= mnoznik

            # 2. Dynamiczne wagi rozdziałów aktywowane tokenami w zapytaniu
            for klucz, warunek in mapa_wag_dyn.items():
                if klucz in tytul:
                    token_aktywujacy = warunek.get("token")
                    mnoznik = warunek.get("mnoznik", 1.0)
                    if token_aktywujacy in wszystkie_tokeny_pytania_set:
                        v *= mnoznik

            mapa_wag[tytul] = v

        if len(aktywne_zdania) == 1:
            # Standardowa ścieżka dla zapytań jednozdaniowych
            zdanie = aktywne_zdania[0]
            tokeny_pytania = tokenizuj(zdanie, slownik_korekcji)
            if not tokeny_pytania:
                return []

            rozszerzenie = []
            for tok in tokeny_pytania:
                if tok in ROZSZERZENIA:
                    dodatkowe = tokenizuj(ROZSZERZENIA[tok])
                    rozszerzenie.extend(dodatkowe)

            pytanie_lower = usun_polskie_znaki(zdanie.lower())
            for fraza, rozszerzenie_frazy in ROZSZERZENIA.items():
                if " " in fraza and fraza in pytanie_lower:
                    rozszerzenie.extend(tokenizuj(rozszerzenie_frazy))

            tokeny_pytania = tokeny_pytania + rozszerzenie
            tf_pytania = oblicz_tf(tokeny_pytania)

            wektor_pytania = {}
            term_boosts = cfg.get("term_boosts", {})
            for slowo, tf_val in tf_pytania.items():
                finalny_tf = tf_val * synonimy_waga if slowo in rozszerzenie else tf_val
                boost = term_boosts.get(slowo, 1.0)
                wektor_pytania[slowo] = finalny_tf * self.idf.get(slowo, 0) * boost

            wyniki = []
            for i, wf in enumerate(wektory_bazy):
                podstawa = podobienstwo_cosinusowe(wektor_pytania, wf)
                tytul = self.fragmenty[i]["tytul"]
                mnoznik = mapa_wag.get(tytul, 1.0)
                wynik_koncowy = podstawa * mnoznik
                wyniki.append((wynik_koncowy, i))
        else:
            # Ścieżka wielozdaniowa (Conversational Multi-sentence Scoring)
            wektory_zdan = []
            term_boosts = cfg.get("term_boosts", {})
            for zdanie in aktywne_zdania:
                tokeny_zdania = tokenizuj(zdanie, slownik_korekcji)
                if not tokeny_zdania:
                    continue

                rozszerzenie = []
                for tok in tokeny_zdania:
                    if tok in ROZSZERZENIA:
                        dodatkowe = tokenizuj(ROZSZERZENIA[tok])
                        rozszerzenie.extend(dodatkowe)

                zdanie_lower = usun_polskie_znaki(zdanie.lower())
                for fraza, rozszerzenie_frazy in ROZSZERZENIA.items():
                    if " " in fraza and fraza in zdanie_lower:
                        rozszerzenie.extend(tokenizuj(rozszerzenie_frazy))

                tokeny_zdania = tokeny_zdania + rozszerzenie
                tf_zdania = oblicz_tf(tokeny_zdania)

                wektor_zdania = {}
                for slowo, tf_val in tf_zdania.items():
                    finalny_tf = (
                        tf_val * synonimy_waga if slowo in rozszerzenie else tf_val
                    )
                    boost = term_boosts.get(slowo, 1.0)
                    wektor_zdania[slowo] = finalny_tf * self.idf.get(slowo, 0) * boost
                wektory_zdan.append(wektor_zdania)

            if not wektory_zdan:
                return []

            wyniki = []
            for i, wf in enumerate(wektory_bazy):
                podobienstwa = [
                    podobienstwo_cosinusowe(wekt, wf) for wekt in wektory_zdan
                ]

                # Scalanie podobieństw: Maximum-Weighted Sum
                if podobienstwa:
                    max_pod = max(podobienstwa)
                    reszta_pod = sum(p for p in podobienstwa if p != max_pod)
                    waga_pobocznych = cfg.get("wyszukiwanie_wielozdaniowe", {}).get(
                        "waga_pobocznych_zdan", 0.25
                    )
                    podstawa = max_pod + waga_pobocznych * reszta_pod
                else:
                    podstawa = 0.0

                tytul = self.fragmenty[i]["tytul"]
                mnoznik = mapa_wag.get(tytul, 1.0)
                wynik_koncowy = podstawa * mnoznik
                wyniki.append((wynik_koncowy, i))

        wyniki.sort(reverse=True)

        confidence_threshold = 0.0
        if virtual_params:
            confidence_threshold = float(
                virtual_params.get("confidence_threshold", 0.0)
            )

        kandydaci = [
            WynikWyszukiwania(
                tytul=self.fragmenty[i]["tytul"],
                tresc=self.fragmenty[i]["tresc"],
                podobienstwo=round(podobienstwo, 4),
                zrodlo=self.fragmenty[i].get("zrodlo"),
            )
            for podobienstwo, i in wyniki
            if podobienstwo >= confidence_threshold and podobienstwo > 0
        ]

        # Filtrowanie po zrodle (dropdown z frontendu)
        zrodla_ignorowane = set(
            cfg.get("szumy_i_wykluczenia", {}).get(
                "zrodla_ignorowane", ["Wszystkie dokumenty", "odlacz"]
            )
        )
        if zrodlo and zrodlo not in zrodla_ignorowane and zrodlo not in ("", None):
            kandydaci = [k for k in kandydaci if k.zrodlo == zrodlo]

        return kandydaci[:n_wynikow]

    def szukaj_wiele(
        self,
        pytania: list[str],
        n_wynikow: int = 1,
        zrodlo: str | None = None,
        virtual_params: dict | None = None,
    ) -> list[list[WynikWyszukiwania]]:
        """
        Dla listy pytań zwraca listę najbardziej pasujących fragmentów.
        Parametry BM25 są przeliczane tylko raz na całe wywołanie.
        """
        cfg = pobierz_konfiguracje()
        bm25_cfg = cfg.get("bm25", {})
        k1_default = float(bm25_cfg.get("k1", 1.5))
        b_default = float(bm25_cfg.get("b", 0.75))
        synonimy_waga = float(bm25_cfg.get("synonimy_waga", 0.85))

        wektory_bazy = self.wektory
        if virtual_params:
            synonimy_waga = float(virtual_params.get("synonym_weight", synonimy_waga))
            k1_lab = float(virtual_params.get("bm25_k1", k1_default))
            b_lab = float(virtual_params.get("bm25_b", b_default))
            if k1_lab != k1_default or b_lab != b_default:
                wektory_bazy = zbuduj_wektory_bm25(
                    self.wszystkie_tokeny, self.idf, custom_k1=k1_lab, custom_b=b_lab
                )

        wyniki_wiele = []
        for pytanie in pytania:
            res = self._szukaj_z_gotowymi_wektorami(
                pytanie,
                wektory_bazy=wektory_bazy,
                synonimy_waga=synonimy_waga,
                n_wynikow=n_wynikow,
                zrodlo=zrodlo,
                virtual_params=virtual_params,
                cfg=cfg,
            )
            wyniki_wiele.append(res)
        return wyniki_wiele

    def szukaj(
        self,
        pytanie: str,
        n_wynikow: int = 1,
        zrodlo: str | None = None,
        virtual_params: dict | None = None,
    ) -> list[WynikWyszukiwania]:
        """
        Dla podanego pytania zwraca n najbardziej pasujacych fragmentow.
        Metoda zachowuje oryginalną sygnaturę i zachowanie, korzystając z szukaj_wiele.
        """
        wyniki = self.szukaj_wiele(
            [pytanie],
            n_wynikow=n_wynikow,
            zrodlo=zrodlo,
            virtual_params=virtual_params,
        )
        return wyniki[0] if wyniki else []


# ── Test ──────────────────────────────────────────────────────────────────────


def main():
    w = Wyszukiwarka([], {}, [], [])  # pusta wyszukiwarka do testów importu

    pytania_testowe = [
        "ile razy mozna powtarzac egzamin",
        "kiedy mozna wziac urlop dziekanski",
        "jak oblicza sie srednia ocen",
        "co grozi za nieobecnosci na zajeciach",
        "kiedy mozna zostac skreslanym z listy studentow",
        "ile semestrów trwają studia inzynierskie",
        "jak wyglada praca dyplomowa",
    ]

    for pytanie in pytania_testowe:
        print(f"Pytanie: {pytanie}")
        wyniki = w.szukaj(pytanie, n_wynikow=1)
        if wyniki:
            w1 = wyniki[0]
            print(f"  Paragraf:     {w1.tytul}")
            print(f"  Podobienstwo: {w1.podobienstwo}")
            print(f"  Fragment:     {w1.tresc[:200]}...")
        print()


if __name__ == "__main__":
    main()
