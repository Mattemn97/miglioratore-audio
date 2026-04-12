import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

class CustomLogger:
    """
    Una classe Logger configurata per essere universale.
    Include formattazione a colori per terminale e salvataggio su file rotativo.
    """
    
    # Codici colore ANSI per il terminale
    _COLORS = {
        'DEBUG': "\033[36m",    # Ciano
        'INFO': "\033[32m",     # Verde
        'WARNING': "\033[33m",  # Giallo
        'ERROR': "\033[31m",    # Rosso
        'CRITICAL': "\033[41m", # Sfondo Rosso
        'RESET': "\033[0m"      # Reset
    }

    @staticmethod
    def get_logger(name: str = "ProjectLogger", log_file: str = "app.log", level=logging.DEBUG):
        """
        Ritorna un'istanza di logger configurata.
        
        :param name: Nome del modulo che genera il log.
        :param log_file: Nome del file dove salvare i log.
        :param level: Livello minimo di logging.
        """
        logger = logging.getLogger(name)

        # Evita di aggiungere handler duplicati se il logger esiste già
        if logger.hasHandlers():
            return logger

        logger.setLevel(level)

        # 1. Formattazione per i log
        file_format = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(message)s (%(filename)s:%(lineno)d)'
        )

        # 2. Handler per il Terminale (con colori)
        class ColorFormatter(logging.Formatter):
            def format(self, record):
                color = CustomLogger._COLORS.get(record.levelname, CustomLogger._COLORS['RESET'])
                reset = CustomLogger._COLORS['RESET']
                record.levelname = f"{color}{record.levelname}{reset}"
                return super().format(record)

        stream_format = ColorFormatter('%(asctime)s | %(levelname)s | %(message)s')
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(stream_format)
        logger.addHandler(stream_handler)

        # 3. Handler per il File (Rotativo: max 5MB per file, tiene 3 backup)
        log_path = Path("logs")
        log_path.mkdir(exist_ok=True) # Crea la cartella logs se non esiste
        
        file_handler = RotatingFileHandler(
            log_path / log_file, 
            maxBytes=5*1024*1024, 
            backupCount=3,
            encoding='utf-8'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)

        return logger

# Singleton preventivo: istanza pre-configurata per uso immediato
logger = CustomLogger.get_logger()
