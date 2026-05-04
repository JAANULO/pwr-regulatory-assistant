import os
from datetime import datetime


def execute_feedback_submission(pid, ocena, base_dir, logger):
    """
    Logika biznesowa obsługująca zapis feedbacku. Zapisuje informację do bazy
    oraz, w przypadku oceny negatywnej dla mało pewnych odpowiedzi, loguje to w pliku TXT.
    """
    try:
        from core.bd import zapisz_feedback, pobierz_pytanie
    except ImportError:
        from ...core.bd import zapisz_feedback, pobierz_pytanie

    zapisz_feedback(pid, ocena)
    logger.info(f"FEEDBACK: pytanie_id={pid}, ocena={ocena}")

    if ocena == -1:
        rekord = pobierz_pytanie(pid)
        if (
            rekord
            and rekord["podobienstwo"] is not None
            and rekord["podobienstwo"] < 0.2
        ):
            log_dir = os.path.join(base_dir, "logs")
            os.makedirs(log_dir, exist_ok=True)
            log_path = os.path.join(log_dir, "do_poprawy.txt")

            with open(log_path, "a", encoding="utf-8") as f:
                czas = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                odpowiedz = rekord.get("odpowiedz") or ""
                f.write(
                    f"[{czas}] Pytanie: '{rekord['pytanie']}' | Odpowiedź: '{odpowiedz}' | Podobieństwo: {rekord['podobienstwo']:.3f} | Tytuł: {rekord['tytul']}\n"
                )

    return True
