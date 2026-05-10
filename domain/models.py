"""
models.py — Obiekty Dziedzinowe (Domain Objects) projektu Asystent PWr v2.

Zastępują rozrzucone słowniki 'dict' ścisłymi typami danych, co umożliwia:
  - statyczne sprawdzanie typów przez mypy
  - lepszą autouzupełnialność w edytorze
  - spójną strukturę odpowiedzi API
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Optional


@dataclass(frozen=True)
class Paragraf:
    """Reprezentuje jeden fragment bazy wiedzy (paragraf regulaminu)."""

    tytul: str
    tresc: str
    zrodlo: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Paragraf":
        return Paragraf(
            tytul=d["tytul"],
            tresc=d["tresc"],
            zrodlo=d.get("zrodlo"),
        )


@dataclass(frozen=True)
class WynikWyszukiwania:
    """Wynik zwrócony przez algorytm BM25 — paragraf + ocena podobieństwa."""

    tytul: str
    tresc: str
    podobienstwo: float
    zrodlo: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "WynikWyszukiwania":
        """Konwertuje istniejący słownik z wyszukiwarki na obiekt."""
        return WynikWyszukiwania(
            tytul=d["tytul"],
            tresc=d["tresc"],
            podobienstwo=d["podobienstwo"],
            zrodlo=d.get("zrodlo"),
        )


@dataclass
class OdpowiedzAPI:
    """Ustrukturyzowana odpowiedź zwracana przez serwis do endpointu /zapytaj."""

    wstep: str
    punkty: list
    tytul: str
    zacheta: str
    podobienstwo: float
    pelna_tresc: str
    pytanie_id: Optional[int] = None
    zrodlo: Optional[str] = None
    tytul2: Optional[str] = None
    podobienstwo2: Optional[float] = None
    zrodlo2: Optional[str] = None
    kontekst_tytul: Optional[str] = None
    slowa_kluczowe: list = field(default_factory=list)
    disambiguation: bool = False
    opcje: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)
