from dataclasses import dataclass

@dataclass(frozen=True)
class Wynik:
    tytul: str

w = Wynik(tytul="Test")
try:
    print(w['tytul'])
except TypeError as e:
    print(f"BŁĄD: {e}")
