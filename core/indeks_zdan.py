"""
indeks_zdan.py – indeks BM25 na poziomie zdań, nie paragrafów.
Zamiast zwracać cały paragraf, zwraca konkretne zdanie z odpowiedzią.

Jak działa:
  Teraz:   pytanie → paragraf (300 słów) → wyciągnij zdania
  Po:      pytanie → konkretne zdanie (1-2 zdania) → gotowa odpowiedź
"""

import re

try:
    from .wyszukiwarka import (
        oblicz_tf,
        podobienstwo_cosinusowe,
        tokenizuj,
    )
except ImportError:
    from wyszukiwarka import (  # type: ignore
        oblicz_tf,
        podobienstwo_cosinusowe,
        tokenizuj,
    )


# ── podział paragrafu na zdania ───────────────────────────────────────────────


def podziel_na_zdania(tresc: str) -> list[str]:
    """
    Dzieli treść paragrafu na pojedyncze zdania.
    Ignoruje skróty typu "ust.", "pkt.", "art."
    """
    # usuń nagłówek paragrafu
    tresc = re.sub(r"^§\s*\d+\.\s*\S[^\n\.]{0,60}\.?\s*", "", tresc).strip()

    # podziel po kropce kończącej zdanie
    podzielony = re.sub(
        r"(?<!\bust)(?<!\bpkt)(?<!\bart)(?<!\bpoz)(?<!\bm\.in)\.\s+(?=[A-ZŁŚŻŹ\d])",
        "|||",
        tresc,
    )
    zdania = []
    for z in podzielony.split("|||"):
        z = z.strip()
        z = re.sub(r"\s*Rozdział\s+[IVX]+[^.]*\.?", "", z).strip()
        z = re.sub(r"\s+", " ", z)
        # minimalna długość – krótsze zdania nie mają wartości informacyjnej
        if len(z) > 40:
            zdania.append(z)
    return zdania


# ── główna klasa ──────────────────────────────────────────────────────────────


class IndeksZdan:
    """
    Buduje indeks BM25 na poziomie zdań.
    Każde zdanie z każdego paragrafu jest osobnym dokumentem.
    """

    def __init__(
        self,
        zdania: list[dict[str, str]],
        idf: dict[str, float],
        wektory: list[dict[str, float]],
    ):
        self.zdania = zdania
        self.idf = idf
        self.wektory = wektory

    def szukaj(self, pytanie: str, n_wynikow: int = 3) -> list[dict]:
        """
        Zwraca n najbardziej pasujących zdań do pytania.
        Każdy wynik zawiera zdanie + paragraf z którego pochodzi.
        """
        from .slowniki import ROZSZERZENIA, ROZSZERZENIA_ZDAN

        try:
            from .wyszukiwarka import usun_polskie_znaki, popraw_literowke
        except ImportError:
            from wyszukiwarka import usun_polskie_znaki, popraw_literowke  # type: ignore

        tokeny = tokenizuj(pytanie)
        if not tokeny:
            return []

        tokeny = [popraw_literowke(t, self.idf) for t in tokeny]

        # rozszerzenie zapytania
        rozszerzenie = []
        for tok in tokeny:
            if tok in ROZSZERZENIA:
                rozszerzenie.extend(tokenizuj(ROZSZERZENIA[tok]))
        pytanie_lower = usun_polskie_znaki(pytanie.lower())
        for fraza, rozszerzenie_frazy in ROZSZERZENIA.items():
            if " " in fraza and fraza in pytanie_lower:
                rozszerzenie.extend(tokenizuj(rozszerzenie_frazy))

        # dodatkowe rozszerzenia specyficzne dla indeksu zdań
        for fraza, rozszerzenie_frazy in ROZSZERZENIA_ZDAN.items():
            if fraza in pytanie_lower:
                rozszerzenie.extend(tokenizuj(rozszerzenie_frazy))

        tokeny = tokeny + rozszerzenie
        tf = oblicz_tf(tokeny)
        wektor_pytania = {s: tf_val * self.idf.get(s, 0) for s, tf_val in tf.items()}

        wyniki = []
        for i, wf in enumerate(self.wektory):
            score = podobienstwo_cosinusowe(wektor_pytania, wf)
            wyniki.append((score, i))

        wyniki.sort(reverse=True)

        return [
            {
                "zdanie": self.zdania[i]["tekst"],
                "tytul": self.zdania[i]["tytul"],
                "tresc_paragrafu": self.zdania[i]["tresc_paragrafu"],
                "zrodlo": self.zdania[i].get("zrodlo"),
                "podobienstwo": round(score, 4),
            }
            for score, i in wyniki[:n_wynikow]
            if score > 0.05
        ]
