import logging
import os

class CustomFormatter(logging.Formatter):
    """Logging Formatter to add colors and count warning / errors"""

    grey = "\x1b[38;21m"
    yellow = "\x1b[33;21m"
    red = "\x1b[31;21m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "%(asctime)s - (%(filename)s:%(lineno)d) - %(levelname)s\n%(message)s"

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: grey + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)
    
log = logging.getLogger("__name__")
debug_level = logging.getLevelName(os.environ.get('DEBUG_LEVEL')) if os.environ.get('DEBUG_LEVEL') is not None else logging.ERROR
log.setLevel(debug_level)
ch = logging.StreamHandler()
ch.setLevel(debug_level)
ch.setFormatter(CustomFormatter())
log.addHandler(ch)
fh = logging.FileHandler('debug.log')
fh.setLevel(debug_level)
file_formatter = logging.Formatter("%(asctime)s [%(levelname)s]\n%(message)s")
fh.setFormatter(file_formatter)
log.addHandler(fh)
