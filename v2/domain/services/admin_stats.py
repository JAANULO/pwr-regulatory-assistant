def execute_admin_eksport_csv(token, admin_token):
    if token != admin_token:
        return "Brak dostępu!", 403

    import csv
    import io
    from flask import Response

    try:
        from core.bd import polacz, TRYB
    except ImportError:
        from ...core.bd import polacz, TRYB

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "Czas",
            "Pytanie Uzytkownika",
            "Tytul Paragrafu",
            "Podobienstwo",
            "Odpowiedz Bota",
            "Ocena Kciuka (-1 zla)",
        ]
    )

    zapytanie = """
        SELECT p.czas, p.pytanie, p.tytul, p.podobienstwo, p.odpowiedz, f.ocena 
        FROM pytania p 
        LEFT JOIN feedback f ON p.id = f.pytanie_id 
        ORDER BY p.id DESC
    """

    if TRYB == "postgres":
        with polacz() as conn:
            with conn.cursor() as cur:
                cur.execute(zapytanie)
                for w in cur.fetchall():
                    writer.writerow(
                        [
                            w["czas"],
                            w["pytanie"],
                            w["tytul"],
                            w["podobienstwo"],
                            w["odpowiedz"],
                            w["ocena"],
                        ]
                    )
    else:
        with polacz() as conn:
            for w in conn.execute(zapytanie).fetchall():
                writer.writerow(
                    [
                        w["czas"],
                        w["pytanie"],
                        w["tytul"],
                        w["podobienstwo"],
                        w["odpowiedz"],
                        w["ocena"],
                    ]
                )

    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=raport_pytan_pwr.csv"},
    )


def execute_admin_dodaj_synonim(dane, admin_token, SYNONIMY, logger):
    token = dane.get("token", "")
    if token != admin_token:
        return {"blad": "Brak dostepu"}, 403
    klucz = dane.get("klucz", "").strip().lower()
    wartosc = dane.get("wartosc", "").strip().lower()
    if klucz and wartosc:
        SYNONIMY[klucz] = wartosc
        logger.info(f"LIVE ADMIN PANEL: Dodano nowe wiazanie RAM: {klucz} -> {wartosc}")
        return {
            "sukces": True,
            "komunikat": f"Wstrzyknięto do RAM: {klucz} -> {wartosc} (Działa natychmiastowo!)",
        }, 200
    return {"blad": "Złe dane wejściowe"}, 400
