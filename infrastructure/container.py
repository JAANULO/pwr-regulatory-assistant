import os
import logging
from typing import TYPE_CHECKING
from core.settings import LOG_LEVEL

if TYPE_CHECKING:
    from core.wyszukiwarka import Wyszukiwarka


class Container:
    """Kontener zależności zarządzający instancjami komponentów."""

    def __init__(self, base_dir: str, data_dir: str, log_file: str):
        self.base_dir = base_dir
        self.data_dir = data_dir
        self.log_file = log_file

        self.wyszukiwarka: "Wyszukiwarka | None" = None
        self.logger: logging.Logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        logger = logging.getLogger("asystent")
        logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

        if not logger.handlers:
            fh = logging.FileHandler(self.log_file, encoding="utf-8")
            fh.setFormatter(
                logging.Formatter(
                    "%(asctime)s | %(levelname)s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
            logger.addHandler(fh)

        logging.getLogger("werkzeug").setLevel(logging.WARNING)
        return logger

    def get_wyszukiwarka(self) -> "Wyszukiwarka":
        from infrastructure.knowledge_loader import utworz_wyszukiwarke

        if not self.wyszukiwarka:
            self.wyszukiwarka = utworz_wyszukiwarke(self.data_dir)
            self.logger.info("Wyszukiwarka zainicjalizowana (DI)")
        return self.wyszukiwarka
