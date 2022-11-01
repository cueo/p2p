import logging


class LogFormatter(logging.Formatter):
    grey = '\x1b[32;1m'
    green = '\x1b[32;1m'
    yellow = "\x1b[33;20m"
    red = '\x1b[31;20m'
    bold_red = '\x1b[31;1m'
    reset = '\x1b[0m'
    format = '%(asctime)s - %(filename)s - %(levelname)s - %(message)s'

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: green + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record: logging.LogRecord) -> str:
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def get_logger(filename, log_level=logging.INFO):
    filename = filename if filename else 'root'
    log = logging.getLogger(filename)
    log.propagate = False
    log.setLevel(log_level)

    ch = logging.StreamHandler()
    ch.setFormatter(LogFormatter())
    log.addHandler(ch)
    return log
