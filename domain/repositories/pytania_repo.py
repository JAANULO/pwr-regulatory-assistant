"""
pytania_repo.py — Repozytorium tabeli `pytania`.

Enkapsuluje wszystkie zapytania SQL dotyczące historii pytań
i statystyk użytkowania. Przyjmuje funkcję połączenia przez DI,
co oddziela logikę od konkretnego backendu (SQLite/PostgreSQL).
"""

from __future__ import annotations

import logging
from typing import Optional

_LOG = logging.getLogger("asystent.db")


def _domyslne_statystyki() -> dict:
    return {
        "pytania": 0,
        "srednie_podobienstwo": 0.0,
        "top_paragrafy": [],
        "zle_odpowiedzi": [],
        "pytania_dzienne": [],
        "ostatnie_pytania": [],
    }


class PytaniaRepository:
    """Repozytorium operacji CRUD na tabeli `pytania`."""

    def __init__(self, polacz_fn, tryb: str, zapytania: dict) -> None:
        self._polacz = polacz_fn
        self._tryb = tryb
        self._zapytania = zapytania

    def zapisz(
        self,
        pytanie: str,
        tytul: Optional[str],
        podobienstwo: Optional[float],
        baza: str = "studia",
        odpowiedz: Optional[str] = None,
    ) -> Optional[int]:
        """Zapisuje pytanie do bazy i zwraca jego ID."""
        if self._tryb == "postgres":
            try:
                with self._polacz() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            self._zapytania["zapisz_pytanie"],
                            (pytanie, tytul, podobienstwo, baza, odpowiedz),
                        )
                        conn.commit()
                        return cur.fetchone()["id"]
            except Exception as e:
                _LOG.warning("Nie udalo sie zapisac pytania (postgres): %s", e)
                return None
        else:
            with self._polacz() as conn:
                cur = conn.execute(
                    self._zapytania["zapisz_pytanie"],
                    (pytanie, tytul, podobienstwo, baza, odpowiedz),
                )
                return cur.lastrowid

    def pobierz(self, pytanie_id: int) -> Optional[dict]:
        """Pobiera zapisane pytanie po ID."""
        if self._tryb == "postgres":
            try:
                with self._polacz() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            self._zapytania["pobierz_pytanie"],
                            (pytanie_id,),
                        )
                        return cur.fetchone()
            except Exception as e:
                _LOG.warning("Nie udalo sie pobrac pytania (postgres): %s", e)
                return None
        else:
            with self._polacz() as conn:
                return conn.execute(
                    self._zapytania["pobierz_pytanie"],
                    (pytanie_id,),
                ).fetchone()

    def pobierz_ostatnie(self, limit: int = 10) -> list:
        """Zwraca ostatnie unikalne pytania do panelu historii."""
        if self._tryb == "postgres":
            try:
                with self._polacz() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            self._zapytania["pobierz_ostatnie"],
                            (limit * 3,),
                        )
                        rows = cur.fetchall()
            except Exception as e:
                _LOG.warning("Nie udalo sie pobrac historii pytan (postgres): %s", e)
                return []
        else:
            with self._polacz() as conn:
                rows = conn.execute(
                    self._zapytania["pobierz_ostatnie"],
                    (limit * 3,),
                ).fetchall()

        unikalne = []
        widziane: set = set()
        for row in rows:
            p = row["pytanie"]
            if p in widziane:
                continue
            widziane.add(p)
            unikalne.append({"pytanie": p})
            if len(unikalne) >= limit:
                break
        return unikalne

    def pobierz_statystyki(self) -> dict:
        """Zwraca agregowane statystyki dla panelu admina."""
        if self._tryb == "postgres":
            try:
                with self._polacz() as conn:
                    with conn.cursor() as cur:
                        cur.execute(self._zapytania["pobierz_statystyki_total"])
                        total = cur.fetchone()["total"]
                        cur.execute(self._zapytania["pobierz_statystyki_avg"])
                        avg = cur.fetchone()["avg"]
                        cur.execute(self._zapytania["pobierz_statystyki_top"])
                        top = cur.fetchall()
                        cur.execute(self._zapytania["pobierz_statystyki_zle"])
                        zle = cur.fetchall()
                        cur.execute(self._zapytania["pobierz_statystyki_dzienne"])
                        dzienne = cur.fetchall()
                        cur.execute(self._zapytania["pobierz_statystyki_ostatnie"])
                        ostatnie = cur.fetchall()
            except Exception as e:
                _LOG.warning("Nie udalo sie pobrac statystyk (postgres): %s", e)
                return _domyslne_statystyki()
        else:
            with self._polacz() as conn:
                total = conn.execute(
                    self._zapytania["pobierz_statystyki_total"]
                ).fetchone()[0]
                avg = conn.execute(
                    self._zapytania["pobierz_statystyki_avg"]
                ).fetchone()[0]
                top = conn.execute(self._zapytania["pobierz_statystyki_top"]).fetchall()
                zle = conn.execute(self._zapytania["pobierz_statystyki_zle"]).fetchall()
                dzienne = conn.execute(
                    self._zapytania["pobierz_statystyki_dzienne"]
                ).fetchall()
                ostatnie = conn.execute(
                    self._zapytania["pobierz_statystyki_ostatnie"]
                ).fetchall()

        return {
            "pytania": total,
            "srednie_podobienstwo": round((avg or 0) * 100, 1),
            "top_paragrafy": [dict(w) for w in top],
            "zle_odpowiedzi": [dict(z) for z in zle],
            "pytania_dzienne": [dict(d) for d in dzienne],
            "ostatnie_pytania": [dict(o) for o in ostatnie],
        }
