import os
import logging
from typing import TYPE_CHECKING
from core.settings import LOG_LEVEL

if TYPE_CHECKING:
    from core.wyszukiwarka import Wyszukiwarka
    from core.indeks_zdan import IndeksZdan


class Container:
    """Kontener zależności zarządzający instancjami komponentów."""

    def __init__(self, base_dir: str, data_dir: str, log_file: str):
        self.base_dir = base_dir
        self.data_dir = data_dir
        self.log_file = log_file

        self.wyszukiwarka: "Wyszukiwarka | None" = None
        self.indeks_zdan: "IndeksZdan | None" = None
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

    def initialize_components(self) -> None:
        """Inicjalizuje wyszukiwarkę i indeks zdań."""
        from infrastructure.knowledge_loader import (
            utworz_wyszukiwarke,
            utworz_indeks_zdan,
        )

        if not self.wyszukiwarka:
            self.wyszukiwarka = utworz_wyszukiwarke(self.data_dir)
            self.logger.info("Wyszukiwarka zainicjalizowana (DI)")

        if not self.indeks_zdan:
            self.indeks_zdan = utworz_indeks_zdan(self.data_dir)
            self.logger.info("Indeks zdań zainicjalizowany (DI)")
