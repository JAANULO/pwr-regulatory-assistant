#  Architektura i Matematyka Projektu

Dokument ten opisuje, jak system działa "pod maską". Przedstawia algorytmy i wzory matematyczne użyte w projekcie, które zostały zaimplementowane od zera, bez użycia gotowych bibliotek (takich jak `scikit-learn` czy `transformers`).

---

## 1. System Wyszukiwania (Asystent Regulaminowy)

Celem systemu jest znalezienie jednego, najbardziej trafnego paragrafu regulaminu na podstawie pytania użytkownika.

### A. Korekta literówek – Odległość Levenshteina
Używamy algorytmu programowania dynamicznego do obliczenia minimalnej liczby operacji (wstawienie, usunięcie, zamiana) potrzebnych do przekształcenia jednego słowa w drugie. W kodzie dopuszczamy maksymalnie **1 błąd edycyjny** dla krótkich słów oraz **2 błędy** dla słów dłuższych niż 8 znaków.

### B. Wektoryzacja tekstu – Algorytm BM25
W przeciwieństwie do klasycznego TF-IDF, zaimplementowano **BM25 (Best Match 25)**. Radzi on sobie ze zjawiskiem "przesycenia" słowami oraz z różną długością paragrafów.

**1. IDF (Odwrotna Częstotliwość Dokumentowa) w wersji Robertsona:**
W kodzie użyto wygładzonej wersji logarytmu, aby uniknąć wartości ujemnych dla bardzo popularnych słów:

$$
\text{IDF}(q_i) = \ln\left(\frac{N - df(q_i) + 0.5}{df(q_i) + 0.5} + 1\right)
$$

Gdzie:
*   $N$: Całkowita liczba dokumentów (paragrafów).
*   $df(q_i)$: Liczba dokumentów zawierających słowo $q_i$.

**2. Główny wzór BM25:**

$$
\text{BM25}(D, Q) = \sum_{i=1}^{n} \text{IDF}(q_i) \cdot \frac{\text{TF}(q_i, D) \cdot (k_1 + 1)}{\text{TF}(q_i, D) + k_1 \cdot \left(1 - b + b \cdot \frac{|D|}{\text{avgdl}}\right)}
$$

Gdzie:
*   $\text{TF}(q_i, D)$: Częstotliwość słowa w danym paragrafie znormalizowana przez jego długość.
*   $|D|$: Długość obecnego paragrafu (liczba słów).
*   $\text{avgdl}$: Średnia długość paragrafu w całej bazie.
*   $k_1 = 1.5$: Współczynnik nasycenia.
*   $b = 0.75$: Normalizacja długości (karanie długich tekstów).

### C. Ranking wyników – Podobieństwo Cosinusowe
Zamiast liczyć euklidesową odległość punktów, liczymy **kąt pomiędzy wektorami** (Podobieństwo Cosinusowe). System skupia się na proporcji użytych słów, ignorując bezwzględną wielkość wektora.

$$
\text{Cosinus}(\theta) = \frac{\mathbf{A} \cdot \mathbf{B}}{\|\mathbf{A}\| \times \|\mathbf{B}\|} = \frac{\sum_{i=1}^{n} A_i B_i}{\sqrt{\sum_{i=1}^{n} A_i^2} \sqrt{\sum_{i=1}^{n} B_i^2}}
$$

*   Wynik bliski **1.0** = wektory wskazują ten sam kierunek (idealne dopasowanie). Próg odcięcia w aplikacji to **0.08** (z dynamicznym dostosowaniem do 0.20 dla długich pytań).

---

## 2. Podsumowanie
Wszystkie powyższe wzory zostały zaimplementowane ręcznie w module `core/wyszukiwarka.py`. System nie korzysta z zewnętrznych bibliotek wektoryzujących, co pozwala na pełną kontrolę nad procesem dopasowania paragrafów do pytań studentów.
