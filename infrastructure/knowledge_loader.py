import os
import glob
import json
import pickle  # nosec B403
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.wyszukiwarka import Wyszukiwarka
    from core.indeks_zdan import IndeksZdan


def utworz_wyszukiwarke(plik_bazy: str) -> "Wyszukiwarka":
    from core.wyszukiwarka import Wyszukiwarka, tokenizuj, oblicz_idf, zbuduj_wektory

    if os.path.isdir(plik_bazy):
        data_dir = plik_bazy
        json_files = sorted(glob.glob(os.path.join(data_dir, "*.json")))
        cache = os.path.join(data_dir, "baza_wiedzy_multi_cache.pkl")
    else:
        data_dir = os.path.dirname(os.path.abspath(plik_bazy))
        json_files = [plik_bazy]
        cache = plik_bazy.replace(".json", "_cache.pkl")

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
        os.path.join(data_dir, "synonimy.toml"),
        os.path.join(data_dir, "rozszerzenia.toml"),
        os.path.join(data_dir, "config.toml"),
    ]
    pliki_sledzone = list(aktywne_pliki) + [s for s in slowniki if os.path.exists(s)]
    baza_mtime = max(os.path.getmtime(p) for p in pliki_sledzone)
    idf = None
    if os.path.exists(cache) and os.path.getmtime(cache) > baza_mtime:
        print("Wczytywanie indeksu z cache...")
        try:
            with open(cache, "rb") as f_pkl:
                idf, wektory, wszystkie_tokeny = pickle.load(f_pkl)  # nosec B301
        except Exception as e:
            print(f"   Ostrzeżenie: Cache uszkodzony ({e}). Buduję indeks na nowo...")
            idf = None

    if idf is None:
        print("Budowanie indeksu TF-IDF...")
        wszystkie_tokeny = []
        for f in fragmenty:
            sklejka = (f["tytul"] + " ") * 3 + f["tresc"]
            wszystkie_tokeny.append(tokenizuj(sklejka))

        idf = oblicz_idf(wszystkie_tokeny)
        wektory = zbuduj_wektory(wszystkie_tokeny, idf)
        try:
            with open(cache, "wb") as f_out:
                pickle.dump((idf, wektory, wszystkie_tokeny), f_out)
            print("   Zapisano cache")
        except Exception as e:
            print(f"   Nie udalo sie zapisac cache (tryb read-only?): {e}")

    print(f"   Zaindeksowano {len(fragmenty)} fragmentow")
    print(f"   Slownik: {len(idf)} unikalnych slow\n")

    return Wyszukiwarka(fragmenty, idf, wektory, wszystkie_tokeny)


def utworz_indeks_zdan(plik_bazy: str) -> "IndeksZdan":
    from core.indeks_zdan import IndeksZdan, podziel_na_zdania
    from core.wyszukiwarka import tokenizuj, oblicz_idf, zbuduj_wektory

    if os.path.isdir(plik_bazy):
        data_dir = plik_bazy
        json_files = sorted(glob.glob(os.path.join(data_dir, "*.json")))
        cache = os.path.join(data_dir, "baza_wiedzy_zdania_cache.pkl")
    else:
        data_dir = os.path.dirname(os.path.abspath(plik_bazy))
        json_files = [plik_bazy]
        cache = plik_bazy.replace(".json", "_zdania_cache.pkl")

    fragmenty = []
    aktywne_pliki = []
    for sciezka in json_files:
        try:
            with open(sciezka, encoding="utf-8") as f_json:
                dane = json.load(f_json)
        except (OSError, json.JSONDecodeError):
            continue

        if not isinstance(dane, list):
            continue

        nazwa_zrodla = os.path.basename(sciezka)
        licznik = 0
        for frag in dane:
            if not isinstance(frag, dict):
                continue
            if "tytul" not in frag or "tresc" not in frag:
                continue
            rekord = dict(frag)
            rekord["zrodlo"] = frag.get("zrodlo", nazwa_zrodla)
            fragmenty.append(rekord)
            licznik += 1

        if licznik > 0:
            aktywne_pliki.append(sciezka)

    if not fragmenty:
        raise FileNotFoundError(
            f"Nie znaleziono poprawnych fragmentow (tytul+tresc) w JSON: {plik_bazy}"
        )

    slowniki = [
        os.path.join(data_dir, "synonimy.toml"),
        os.path.join(data_dir, "rozszerzenia.toml"),
    ]
    pliki_sledzone = list(aktywne_pliki) + [s for s in slowniki if os.path.exists(s)]
    baza_mtime = max(os.path.getmtime(p) for p in pliki_sledzone)
    if os.path.exists(cache) and os.path.getmtime(cache) > baza_mtime:
        try:
            with open(cache, "rb") as f_pkl:
                zdania, idf, wektory = pickle.load(f_pkl)  # nosec B301
            print(f"  Indeks zdan: {len(zdania)} zdan (z cache)")
            return IndeksZdan(zdania, idf, wektory)
        except Exception as e:
            print(f"  Ostrzeżenie: Cache zdan uszkodzony ({e}). Buduję na nowo...")

    zdania = []
    for fragment in fragmenty:
        for zdanie in podziel_na_zdania(fragment["tresc"]):
            zdania.append(
                {
                    "tekst": zdanie,
                    "tytul": fragment["tytul"],
                    "tresc_paragrafu": fragment["tresc"],
                    "zrodlo": fragment.get("zrodlo"),
                }
            )

    wszystkie_tokeny = [tokenizuj(z["tekst"]) for z in zdania]
    idf = oblicz_idf(wszystkie_tokeny)
    wektory = zbuduj_wektory(wszystkie_tokeny, idf)

    try:
        with open(cache, "wb") as f_out:
            pickle.dump((zdania, idf, wektory), f_out)
    except Exception as e:
        print(f"  Nie udalo sie zapisac cache (tryb read-only?): {e}")

    print(f"  Indeks zdan: {len(zdania)} zdan z {len(fragmenty)} paragrafow")
    return IndeksZdan(zdania, idf, wektory)
