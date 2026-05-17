def execute_simulate_question(dane, wyszukiwarka, logger):
    """
    Logika biznesowa dla endpointu /zapytaj_symulacja.
    Przeprowadza wyszukiwanie z użyciem BM25 w dwóch wariantach (Baseline i Delta).
    """
    pytanie = dane.get("pytanie", "").strip()

    virtual_params = {
        "bm25_k1": float(dane.get("k1", 1.5)),
        "bm25_b": float(dane.get("b", 0.75)),
        "synonym_weight": float(dane.get("syn_weight", 1.0)),
        "confidence_threshold": float(dane.get("threshold", 0.0)),
    }

    if not pytanie:
        return {"blad": "Puste pytanie"}, 400

    # Symulacja BASE
    wyniki_base = wyszukiwarka.szukaj(pytanie, n_wynikow=1)
    b_score = wyniki_base[0].podobienstwo if wyniki_base else 0.0

    # Symulacja DELTA
    try:
        wyniki_delta = wyszukiwarka.szukaj(
            pytanie, n_wynikow=1, virtual_params=virtual_params
        )
        d_score = wyniki_delta[0].podobienstwo if wyniki_delta else 0.0
        d_title = wyniki_delta[0].tytul if wyniki_delta else "Brak"
    except Exception as e:
        logger.error(f"BLAD LAB DELTA: {e}")
        d_score = 0.0
        d_title = "ERROR"

    return {
        "base_score": b_score,
        "delta_score": d_score,
        "delta_title": d_title,
        "base_title": wyniki_base[0].tytul if wyniki_base else "Brak",
    }, 200
