import os
import glob
import json
import pickle  # nosec B403
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.wyszukiwarka import Wyszukiwarka


def utworz_wyszukiwarke(plik_bazy: str) -> "Wyszukiwarka":
    from core.wyszukiwarka import (
        Wyszukiwarka,
        tokenizuj,
        oblicz_idf_bm25,
        zbuduj_wektory_bm25,
        pobierz_konfiguracje,
    )

    cfg = pobierz_konfiguracje()
    mnoznik_tytulu = int(cfg.get("nlp", {}).get("tytul_mnoznik", 3))

    if os.path.isdir(plik_bazy):
        data_dir = plik_bazy
        kb_dir = os.path.join(data_dir, "kb")
        if os.path.isdir(kb_dir):
            json_files = sorted(glob.glob(os.path.join(kb_dir, "*.json")))
        else:
            json_files = sorted(glob.glob(os.path.join(data_dir, "*.json")))
        cache = os.path.join(data_dir, "database", "baza_wiedzy_multi_cache.pkl")
        data_root = data_dir
    else:
        data_root = os.path.dirname(os.path.abspath(plik_bazy))
        if os.path.basename(data_root) == "kb":
            data_root = os.path.dirname(data_root)
        json_files = [plik_bazy]
        cache = os.path.join(data_root, "database", "baza_wiedzy_multi_cache.pkl")

    if not json_files:
        raise FileNotFoundError(f"Brak plikow JSON do indeksowania w: {plik_bazy}")

    print("Ladowanie bazy wiedzy...")
    fragmenty = []
    aktywne_pliki = []
    for sciezka in json_files:
        try:
            with open(sciezka, "r", encoding="utf-8") as f_json:
                dane = json.load(f_json)
        except (OSError, json.JSONDecodeError):
            continue

        if not isinstance(dane, list):
            continue

        nazwa_zrodla = os.path.basename(sciezka)
        fragmenty_z_pliku = 0
        for frag in dane:
            if not isinstance(frag, dict):
                continue
            if "tytul" not in frag or "tresc" not in frag:
                continue
            rekord = dict(frag)
            rekord["zrodlo"] = frag.get("zrodlo", nazwa_zrodla)
            fragmenty.append(rekord)
            fragmenty_z_pliku += 1

        if fragmenty_z_pliku > 0:
            aktywne_pliki.append(sciezka)

    if not fragmenty:
        raise FileNotFoundError(
            f"Nie znaleziono poprawnych fragmentow (tytul+tresc) w JSON: {plik_bazy}"
        )

    slowniki = [
        os.path.join(data_root, "config", "synonimy.toml"),
        os.path.join(data_root, "config", "rozszerzenia.toml"),
        os.path.join(data_root, "config", "config.toml"),
    ]
    pliki_sledzone = list(aktywne_pliki) + [s for s in slowniki if os.path.exists(s)]
    baza_mtime = max(os.path.getmtime(p) for p in pliki_sledzone)
    idf = None
    if os.path.exists(cache) and os.path.getmtime(cache) > baza_mtime:
        print("Wczytywanie indeksu z cache...")
        try:
            with open(cache, "rb") as f_pkl:
                idf, wektory, wszystkie_tokeny = pickle.load(f_pkl)  # nosec B301
            if len(wektory) != len(fragmenty):
                print(
                    "   Ostrzeżenie: Cache nie pasuje do rozmiaru wczytanej bazy. Buduję od nowa..."
                )
                idf = None
        except Exception as e:
            print(f"   Ostrzeżenie: Cache uszkodzony ({e}). Buduję indeks na nowo...")
            idf = None

    if idf is None:
        print("Budowanie indeksu TF-IDF...")
        wszystkie_tokeny = []
        for f in fragmenty:
            sklejka = (f["tytul"] + " ") * mnoznik_tytulu + f["tresc"]
            wszystkie_tokeny.append(tokenizuj(sklejka))

        idf = oblicz_idf_bm25(wszystkie_tokeny)
        wektory = zbuduj_wektory_bm25(wszystkie_tokeny, idf)
        try:
            with open(cache, "wb") as f_out:
                pickle.dump((idf, wektory, wszystkie_tokeny), f_out)
            print("   Zapisano cache")
        except Exception as e:
            print(f"   Nie udalo sie zapisac cache (tryb read-only?): {e}")

    print(f"   Zaindeksowano {len(fragmenty)} fragmentow")
    print(f"   Slownik: {len(idf)} unikalnych slow\n")

    return Wyszukiwarka(fragmenty, idf, wektory, wszystkie_tokeny)
