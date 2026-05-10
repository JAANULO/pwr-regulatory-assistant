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

    def __init__(self, polacz_fn, tryb: str) -> None:
        self._polacz = polacz_fn
        self._tryb = tryb

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
                            "INSERT INTO pytania (pytanie, tytul, podobienstwo, baza, odpowiedz) VALUES (%s,%s,%s,%s,%s) RETURNING id",
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
                    "INSERT INTO pytania (pytanie, tytul, podobienstwo, baza, odpowiedz) VALUES (?,?,?,?,?)",
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
                            "SELECT pytanie, tytul, podobienstwo, odpowiedz FROM pytania WHERE id = %s",
                            (pytanie_id,),
                        )
                        return cur.fetchone()
            except Exception as e:
                _LOG.warning("Nie udalo sie pobrac pytania (postgres): %s", e)
                return None
        else:
            with self._polacz() as conn:
                return conn.execute(
                    "SELECT pytanie, tytul, podobienstwo, odpowiedz FROM pytania WHERE id = ?",
                    (pytanie_id,),
                ).fetchone()

    def pobierz_ostatnie(self, limit: int = 10) -> list:
        """Zwraca ostatnie unikalne pytania do panelu historii."""
        if self._tryb == "postgres":
            try:
                with self._polacz() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "SELECT pytanie FROM pytania WHERE pytanie IS NOT NULL AND pytanie <> '' ORDER BY id DESC LIMIT %s",
                            (limit * 3,),
                        )
                        rows = cur.fetchall()
            except Exception as e:
                _LOG.warning("Nie udalo sie pobrac historii pytan (postgres): %s", e)
                return []
        else:
            with self._polacz() as conn:
                rows = conn.execute(
                    "SELECT pytanie FROM pytania WHERE pytanie IS NOT NULL AND pytanie <> '' ORDER BY id DESC LIMIT ?",
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
                        cur.execute("SELECT COUNT(*) as total FROM pytania")
                        total = cur.fetchone()["total"]
                        cur.execute("SELECT AVG(podobienstwo) as avg FROM pytania")
                        avg = cur.fetchone()["avg"]
                        cur.execute("""
                            SELECT tytul, COUNT(*) as n
                            FROM pytania WHERE tytul IS NOT NULL
                            GROUP BY tytul ORDER BY n DESC LIMIT 5
                        """)
                        top = cur.fetchall()
                        cur.execute("""
                            SELECT p.pytanie, p.tytul, p.podobienstwo
                            FROM feedback f
                                     JOIN pytania p ON f.pytanie_id = p.id
                            WHERE f.ocena = -1
                            ORDER BY f.czas DESC LIMIT 10
                        """)
                        zle = cur.fetchall()
                        cur.execute("""
                            SELECT TO_CHAR(czas::timestamp, 'YYYY-MM-DD') as dzien, COUNT(*) as liczba
                            FROM pytania
                            GROUP BY dzien
                            ORDER BY dzien LIMIT 30
                        """)
                        dzienne = cur.fetchall()
                        cur.execute("""
                            SELECT czas, pytanie, odpowiedz, podobienstwo
                            FROM pytania
                            ORDER BY id DESC LIMIT 50
                        """)
                        ostatnie = cur.fetchall()
            except Exception as e:
                _LOG.warning("Nie udalo sie pobrac statystyk (postgres): %s", e)
                return _domyslne_statystyki()
        else:
            with self._polacz() as conn:
                total = conn.execute("SELECT COUNT(*) FROM pytania").fetchone()[0]
                avg = conn.execute("SELECT AVG(podobienstwo) FROM pytania").fetchone()[
                    0
                ]
                top = conn.execute("""
                    SELECT tytul, COUNT(*) as n
                    FROM pytania WHERE tytul IS NOT NULL
                    GROUP BY tytul ORDER BY n DESC LIMIT 5
                """).fetchall()
                zle = conn.execute("""
                    SELECT p.pytanie, p.tytul, p.podobienstwo
                    FROM feedback f
                             JOIN pytania p ON f.pytanie_id = p.id
                    WHERE f.ocena = -1
                    ORDER BY f.czas DESC LIMIT 10
                """).fetchall()
                dzienne = conn.execute("""
                    SELECT substr(czas, 1, 10) as dzien, COUNT(*) as liczba
                    FROM pytania
                    GROUP BY substr(czas, 1, 10)
                    ORDER BY dzien LIMIT 30
                """).fetchall()
                ostatnie = conn.execute("""
                    SELECT czas, pytanie, odpowiedz, podobienstwo
                    FROM pytania
                    ORDER BY id DESC LIMIT 50
                """).fetchall()

        return {
            "pytania": total,
            "srednie_podobienstwo": round((avg or 0) * 100, 1),
            "top_paragrafy": [dict(w) for w in top],
            "zle_odpowiedzi": [dict(z) for z in zle],
            "pytania_dzienne": [dict(d) for d in dzienne],
            "ostatnie_pytania": [dict(o) for o in ostatnie],
        }
