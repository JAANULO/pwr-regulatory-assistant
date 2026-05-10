import os
import threading
from datetime import datetime


def _background_save(pid, ocena, base_dir, logger):
    """Faktyczny zapis wykonujący się w osobnym wątku."""
    try:
        from core.bd import zapisz_feedback, pobierz_pytanie
    except ImportError:
        from ...core.bd import zapisz_feedback, pobierz_pytanie

    try:
        zapisz_feedback(pid, ocena)
        logger.info(f"FEEDBACK_ASYNC: pytanie_id={pid}, ocena={ocena}")

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
    except Exception as e:
        logger.error(f"BLAD_FEEDBACK_ASYNC: {e}")


def execute_feedback_submission(pid, ocena, base_dir, logger):
    """
    Inicjuje asynchroniczny zapis feedbacku.
    """
    thread = threading.Thread(
        target=_background_save, args=(pid, ocena, base_dir, logger)
    )
    thread.daemon = True  # Wątek zostanie zabity przy zamknięciu aplikacji
    thread.start()
    return True
