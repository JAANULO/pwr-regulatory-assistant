import logging
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from core.wyszukiwarka import Wyszukiwarka


def execute_ask_question(
    pytanie: str,
    filtr_zrodlo: str | None,
    kontekst_tytul: str | None,
    kontekst_pytanie: str | None,
    wyszukiwarka: "Wyszukiwarka",
    logger: logging.Logger,
    cache_get_fn: Callable[[str], Any],
    cache_set_fn: Callable[[str, Any], None],
    znajdz_rozszerzenie_fn: Callable[[str], str],
    MAPA_ZNAKOW: dict[int, Any],
    SYNONIMY: dict[str, str],
) -> dict:
    """
    Wyodrębniona logika biznesowa z endpointu /zapytaj.
    Przetwarza zapytanie użytkownika, obsługuje rozszerzanie kontekstu,
    podobieństwa z BM25, disambiguację oraz generowanie skrótów/odpowiedzi.
    """
    from core.formatowanie import formatuj_odpowiedz
    from core.bd import zapisz_pytanie
    from core.wyszukiwarka import tokenizuj
    from core.intencje import (
        wykryj_intencje,
    )

    cache_dozwolony = kontekst_tytul is None
    if cache_dozwolony:
        cached = cache_get_fn(pytanie)
        if cached is not None:
            return cached

    # 1. Sprawdzenie czy pytanie odnosi się wprost do konkretnego paragrafu
    numer_paragrafu = wyszukiwarka.wykryj_numer_paragrafu(pytanie)
    if numer_paragrafu:
        wynik_bezposredni = wyszukiwarka.pobierz_paragraf_po_numerze(numer_paragrafu)
        if wynik_bezposredni:
            odp = formatuj_odpowiedz(pytanie, wynik_bezposredni)
            tekst_odpowiedzi = odp["wstep"] if isinstance(odp, dict) else odp
            pid = zapisz_pytanie(
                pytanie,
                wynik_bezposredni.tytul,
                wynik_bezposredni.podobienstwo,
                odpowiedz=tekst_odpowiedzi,
            )
            logger.info(
                f"DIRECT_PARAGRAF: pid={pid}, paragraf={numer_paragrafu}, tytul='{wynik_bezposredni.tytul}'"
            )

            if isinstance(odp, dict):
                payload = {
                    "wstep": odp["wstep"],
                    "punkty": odp["punkty"],
                    "tytul": odp["tytul"],
                    "zacheta": odp["zacheta"],
                    "podobienstwo": odp["podobienstwo"],
                    "pelna_tresc": odp["pelna_tresc"],
                    "tytul2": None,
                    "podobienstwo2": None,
                    "pytanie_id": pid,
                    "kontekst_tytul": odp["tytul"],
                    "zrodlo": wynik_bezposredni.zrodlo,
                }
                if cache_dozwolony:
                    cache_set_fn(pytanie, payload)
                return payload

            payload = {
                "odpowiedz": odp,
                "tytul": wynik_bezposredni.tytul,
                "podobienstwo": 1.0,
                "pytanie_id": pid,
                "zrodlo": wynik_bezposredni.zrodlo,
            }
            if cache_dozwolony:
                cache_set_fn(pytanie, payload)
            return payload

    # 1.5. Sprawdzenie czy pytanie odnosi się do definicji pojęć z § 2 Słownika
    from core.szybkie_odpowiedzi import dopasuj_szybka_odpowiedz

    szybka_def = dopasuj_szybka_odpowiedz(pytanie)
    if szybka_def:
        wynik_bezposredni = wyszukiwarka.pobierz_paragraf_po_numerze(2)
        if wynik_bezposredni:
            pid = zapisz_pytanie(
                pytanie,
                wynik_bezposredni.tytul,
                wynik_bezposredni.podobienstwo,
                odpowiedz=szybka_def,
            )
            payload = {
                "odpowiedz": szybka_def,
                "tytul": wynik_bezposredni.tytul,
                "podobienstwo": 1.0,
                "pelna_tresc": wynik_bezposredni.tresc,
                "tytul2": None,
                "podobienstwo2": None,
                "pytanie_id": pid,
                "kontekst_tytul": wynik_bezposredni.tytul,
                "zrodlo": wynik_bezposredni.zrodlo,
            }
            if cache_dozwolony:
                cache_set_fn(pytanie, payload)
            return payload

    rozszerzenie = znajdz_rozszerzenie_fn(pytanie.lower())
    pytanie_do_szukania = (
        (pytanie + " " + rozszerzenie).strip() if rozszerzenie else pytanie
    )

    # 2. Wykryj pytania kontekstowe
    SYGNALY_KONTEKSTU = [
        "a co jak",
        "a jesli",
        "a jezeli",
        "co jak",
        "co jesli",
        "a co jesli",
        "i co wtedy",
        "co wtedy",
        "a wtedy",
        "a jak nie",
        "jak nie zdam",
        "jak obleje",
        "co jak nie",
        "a czy moge",
        "czy wtedy",
        "co z tym",
        "i co z",
    ]
    pyt_ascii = pytanie.lower().translate(MAPA_ZNAKOW)

    jest_kontekstowe = (
        kontekst_tytul is not None
        and len(pytanie.split()) <= 7
        and any(s in pyt_ascii for s in SYGNALY_KONTEKSTU)
    )
    logger.debug(
        f"jest_kontekstowe={jest_kontekstowe}, tytul={kontekst_tytul}, len={len(pytanie.split())}, ascii={pyt_ascii}"
    )

    if jest_kontekstowe and kontekst_pytanie:
        pytanie_do_szukania = kontekst_pytanie + " " + pytanie
        logger.info(f"KONTEKST: rozszerzam pytanie o '{kontekst_pytanie}'")

    if len(pytanie.split()) <= 2:
        slowo_bazowe = pytanie.strip().lower().rstrip("?!")
        pasujace = [v for k, v in SYNONIMY.items() if slowo_bazowe in k]
        if pasujace:
            pytanie_do_szukania = pytanie + " " + " ".join(set(pasujace))

    # 3. Szukanie w BM25
    wyniki = wyszukiwarka.szukaj(pytanie_do_szukania, n_wynikow=3, zrodlo=filtr_zrodlo)
    wynik = wyniki[0] if wyniki else None

    wynik2 = None
    if len(wyniki) >= 2:
        roznica = wyniki[0].podobienstwo - wyniki[1].podobienstwo

        # Disambiguator
        if (
            roznica <= 0.04
            and len(pytanie.split()) <= 4
            and wyniki[0].podobienstwo >= 0.12
        ):
            pid = zapisz_pytanie(
                pytanie, None, wyniki[0].podobienstwo, odpowiedz="[SYSTEM WAHAŃ]"
            )
            logger.info(
                f"DISAMBIGUATION: pytanie='{pytanie}' -> {wyniki[0].tytul} vs {wyniki[1].tytul}"
            )
            return {
                "disambiguation": True,
                "pytanie_id": pid,
                "komunikat": "Och! Twoje zapytanie jest delikatnie ogólnikowe i dotyka stref dwóch podobnych tematów. O który dokładnie ustęp Ci chodzi?",
                "opcje": [wyniki[0].tytul, wyniki[1].tytul],
            }

        if roznica < 0.03 and len(pytanie.split()) >= 6:
            wynik2 = wyniki[1]

    # 4. Progi i brak trafienia
    dynamiczny_prog = max(0.08, min(0.20, 0.05 + (len(pytanie.split()) * 0.02)))
    prog = 0.10 if jest_kontekstowe else dynamiczny_prog

    if not wynik or wynik.podobienstwo < prog:
        pod = wynik.podobienstwo if wynik else 0.0
        propozycje = [w.tytul for w in wyniki[:3] if w.podobienstwo > 0.05]
        tekst = "Nie znalazłem dokładnej odpowiedzi w regulaminie."

        if propozycje:
            tekst += f" Może chodzi o: {', '.join(propozycje[:2])}?"
        pid = zapisz_pytanie(pytanie, None, pod, odpowiedz=tekst)
        logger.info(
            f"BRAK_TRAFIENIA: pytanie='{pytanie}', najlepsze={pod:.3f}, pid={pid}"
        )

        payload = {
            "odpowiedz": tekst,
            "tytul": None,
            "podobienstwo": pod,
            "tytul2": None,
            "pytanie_id": pid,
            "zrodlo": None,
        }
        if cache_dozwolony:
            cache_set_fn(pytanie, payload)
        return payload

    intencja = wykryj_intencje(pytanie)
    najlepsze_zdanie = None
    skrot = None

    if intencja in ("SKUTEK", "TAK_NIE") and najlepsze_zdanie:
        odp = formatuj_odpowiedz(
            pytanie,
            wynik,
            najlepsze_zdanie=najlepsze_zdanie,
            skrot=skrot,
            tylko_jedno=True,
        )
    else:
        odp = formatuj_odpowiedz(
            pytanie, wynik, najlepsze_zdanie=najlepsze_zdanie, skrot=skrot
        )

    tekst_odpowiedzi = odp["wstep"] if isinstance(odp, dict) else odp
    pid = zapisz_pytanie(
        pytanie, wynik.tytul, wynik.podobienstwo, odpowiedz=tekst_odpowiedzi
    )
    logger.info(
        f"ODPOWIEDZ: pid={pid}, tytul='{wynik.tytul}', podobienstwo={wynik.podobienstwo:.4f}"
    )

    if isinstance(odp, dict):
        payload = {
            "wstep": odp["wstep"],
            "punkty": odp["punkty"],
            "tytul": odp["tytul"],
            "zacheta": odp["zacheta"],
            "slowa_kluczowe": tokenizuj(pytanie),
            "podobienstwo": odp["podobienstwo"],
            "pelna_tresc": odp["pelna_tresc"],
            "tytul2": wynik2.tytul if wynik2 else None,
            "podobienstwo2": wynik2.podobienstwo if wynik2 else None,
            "pytanie_id": pid,
            "kontekst_tytul": odp["tytul"],
            "zrodlo": wynik.zrodlo,
            "zrodlo2": wynik2.zrodlo if wynik2 else None,
        }
        if cache_dozwolony:
            cache_set_fn(pytanie, payload)
        return payload

    payload = {
        "odpowiedz": odp,
        "tytul": None,
        "podobienstwo": 0,
        "pytanie_id": pid,
        "zrodlo": None,
    }
    if cache_dozwolony:
        cache_set_fn(pytanie, payload)
    return payload
