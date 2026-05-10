"""
feedback_repo.py — Repozytorium tabeli `feedback`.

Enkapsuluje zapytania SQL dotyczące ocen użytkowników
i generowania map wag dla algorytmu BM25.
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Optional

_LOG = logging.getLogger("asystent.db")


class FeedbackRepository:
    """Repozytorium operacji na tabeli `feedback`."""

    def __init__(self, polacz_fn, tryb: str) -> None:
        self._polacz = polacz_fn
        self._tryb = tryb

    def zapisz(
        self,
        pytanie_id: int,
        ocena: int,
        komentarz: Optional[str] = None,
    ) -> bool:
        """Zapisuje ocenę użytkownika do bazy."""
        if self._tryb == "postgres":
            try:
                with self._polacz() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "INSERT INTO feedback (pytanie_id, ocena, komentarz) VALUES (%s,%s,%s)",
                            (pytanie_id, ocena, komentarz),
                        )
                        conn.commit()
            except Exception as e:
                _LOG.warning("Nie udalo sie zapisac feedbacku (postgres): %s", e)
        else:
            with self._polacz() as conn:
                conn.execute(
                    "INSERT INTO feedback (pytanie_id, ocena, komentarz) VALUES (?,?,?)",
                    (pytanie_id, ocena, komentarz),
                )
        return True

    def pobierz_wspolczynniki_zbiorczo(self) -> dict:
        """
        Zwraca mapę wag paragrafów na podstawie zbiorczego feedbacku.
        Używane przez algorytm BM25 do modyfikacji rankingu wyników.
        Wartość > 1.0 oznacza, że paragraf jest często oceniany pozytywnie.
        """
        zapytanie = """
            SELECT p.tytul, SUM(f.ocena) as suma_ocen
            FROM feedback f
            JOIN pytania p ON f.pytanie_id = p.id
            WHERE p.tytul IS NOT NULL
            GROUP BY p.tytul
        """
        if self._tryb == "postgres":
            try:
                with self._polacz() as conn:
                    with conn.cursor() as cur:
                        cur.execute(zapytanie)
                        wyniki = cur.fetchall()
            except Exception as e:
                _LOG.warning("Nie udalo sie pobrac wspolczynnikow (postgres): %s", e)
                return {}
        else:
            try:
                with self._polacz() as conn:
                    wyniki = conn.execute(zapytanie).fetchall()
            except sqlite3.OperationalError:
                # Tabela feedback może nie istnieć przy pierwszym uruchomieniu lub w CI
                return {}

        slownik = {}
        for w in wyniki:
            suma = w["suma_ocen"]
            if suma > 0:
                slownik[w["tytul"]] = 1.2
            elif suma < 0:
                slownik[w["tytul"]] = 0.8
            else:
                slownik[w["tytul"]] = 1.0
        return slownik
