-- name: zapisz_feedback
INSERT INTO feedback (pytanie_id, ocena, komentarz) VALUES (%s,%s,%s);

-- name: pobierz_wspolczynniki_zbiorczo
SELECT p.tytul, SUM(f.ocena) as suma_ocen
FROM feedback f
JOIN pytania p ON f.pytanie_id = p.id
WHERE p.tytul IS NOT NULL
GROUP BY p.tytul;

-- name: zapisz_pytanie
INSERT INTO pytania (pytanie, tytul, podobienstwo, baza, odpowiedz) VALUES (%s,%s,%s,%s,%s) RETURNING id;

-- name: pobierz_pytanie
SELECT pytanie, tytul, podobienstwo, odpowiedz FROM pytania WHERE id = %s;

-- name: pobierz_ostatnie
SELECT pytanie FROM pytania WHERE pytanie IS NOT NULL AND pytanie <> '' ORDER BY id DESC LIMIT %s;

-- name: pobierz_statystyki_total
SELECT COUNT(*) as total FROM pytania;

-- name: pobierz_statystyki_avg
SELECT AVG(podobienstwo) as avg FROM pytania;

-- name: pobierz_statystyki_top
SELECT tytul, COUNT(*) as n
FROM pytania WHERE tytul IS NOT NULL
GROUP BY tytul ORDER BY n DESC LIMIT 5;

-- name: pobierz_statystyki_zle
SELECT p.pytanie, p.tytul, p.podobienstwo
FROM feedback f
JOIN pytania p ON f.pytanie_id = p.id
WHERE f.ocena = -1
ORDER BY f.czas DESC LIMIT 10;

-- name: pobierz_statystyki_dzienne
SELECT TO_CHAR(czas::timestamp, 'YYYY-MM-DD') as dzien, COUNT(*) as liczba
FROM pytania
GROUP BY dzien
ORDER BY dzien LIMIT 30;

-- name: pobierz_statystyki_ostatnie
SELECT czas, pytanie, odpowiedz, podobienstwo
FROM pytania
ORDER BY id DESC LIMIT 50;
