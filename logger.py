import logging
from logging import Handler
import os
import urllib.parse
import requests

class TelegramHandler(Handler):
    def emit(self, record):
        log_entry = self.format(record)
        token = "1321535286:AAEpm9JB4zDhkANld8C4ct1-fUyAwkPCOHI"
        channel = "-1001232544210"
        message = urllib.parse.quote(log_entry)
        return requests.get(f"https://api.telegram.org/bot{token}/sendMessage?chat_id={channel}&text={message}")
    
class CustomFormatter(logging.Formatter):
    """Logging Formatter to add colors and count warning / errors"""

    grey = "\x1b[38;21m"
    yellow = "\x1b[33;21m"
    red = "\x1b[31;21m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    _format = "%(asctime)s - (%(filename)s:%(lineno)d) - %(levelname)s\n%(message)s"

    FORMATS = {
        logging.DEBUG: grey + _format + reset,
        logging.INFO: grey + _format + reset,
        logging.WARNING: yellow + _format + reset,
        logging.ERROR: red + _format + reset,
        logging.CRITICAL: bold_red + _format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)
    
log = logging.getLogger("__name__")
debug_level = logging.getLevelName(os.environ.get('LOG_LEVEL')) if os.environ.get('LOG_LEVEL') is not None else logging.ERROR
log.setLevel(debug_level)
#console
ch = logging.StreamHandler()
ch.setLevel(debug_level)
ch.setFormatter(CustomFormatter())
log.addHandler(ch)
#file
fh = logging.FileHandler('debug.log')
fh.setLevel(debug_level)
file_formatter = logging.Formatter("%(asctime)s [%(levelname)s]\n%(message)s")
fh.setFormatter(file_formatter)
log.addHandler(fh)
#telegram
th = TelegramHandler()
th.setLevel(logging.ERROR)
telegram_formatter = logging.Formatter("[%(levelname)s]\n%(message)s")
th.setFormatter(telegram_formatter)
log.addHandler(th)
