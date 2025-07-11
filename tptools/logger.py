import logging
import click

logging.TRACE = logging.DEBUG - 1

logging.addLevelName(logging.TRACE, "TRACE")


class CustomFormatter(logging.Formatter):
    GREY = "\x1b[48;5;15m\x1b[38;5;7m"
    CYAN = "\x1b[48;5;15m\x1b[38;5;14m"
    YELLOW = "\x1b[48;5;11m\x1b[38;5;0m"
    RED = "\x1b[48;5;15m\x1b[38;5;9m"
    BOLD_RED = "\x1b[48;5;9m\x1b[38;5;15m"
    RESET = "\x1b[0m"

    FORMATS = {
        logging.TRACE: f"{GREY}%(fmt)s{RESET}",
        logging.DEBUG: f"{CYAN}%(fmt)s{RESET}",
        logging.INFO: "%(fmt)s",
        logging.WARNING: f"{YELLOW}%(fmt)s{RESET}",
        logging.ERROR: f"{RED}%(fmt)s{RESET}",
        logging.CRITICAL: f"{BOLD_RED}%(fmt)s{RESET}",
    }

    def __init__(
        self,
        fmt=None,
        datefmt=None,
        style="%",
        validate=True,
        *,
        defaults=None,
    ):
        self._formats = dict(
            (k, v % dict(fmt=fmt)) for k, v in CustomFormatter.FORMATS.items()
        )
        super().__init__(fmt, datefmt, style, validate, defaults=defaults)

    def format(self, record):
        self._style._fmt = self._formats.get(record.levelno)
        return super().format(record)


class ClickStyleFormatter(logging.Formatter):

    STYLES = {
        logging.TRACE: {"fg": "bright_cyan"},
        logging.DEBUG: {"fg": "cyan"},
        logging.INFO: {},
        logging.WARNING: {"fg": "black", "bg": "bright_yellow"},
        logging.ERROR: {"fg": "white", "bg": "bright_red", "bold": True},
        logging.CRITICAL: {
            "fg": "bright_yellow",
            "bg": "bright_red",
            "bold": True,
            "blink": True,
        },
    }

    def format(self, record):
        style = self.STYLES.get(record.levelno, {})
        message = super().format(record)
        return click.style(message, **style)


class ClickEchoHandler(logging.StreamHandler):
    def emit(self, record):
        msg = self.format(record)
        click.echo(msg + self.terminator, nl=False, file=self.stream)


def get_logger(name=None, level=logging.INFO):

    logger = logging.getLogger(name)
    logger.setLevel(level)

    streamhandler = ClickEchoHandler()
    fmt = (
        "%(asctime)s %(levelname)-8s %(message)s "
        "(%(filename)s:%(lineno)d, logger: %(name)s)"
    )
    formatter = ClickStyleFormatter(
        fmt=fmt,
        datefmt="%F %T",
    )
    streamhandler.setFormatter(formatter)

    logger.addHandler(streamhandler)

    def trace(msg, *args, **kwargs):
        return logger.log(logging.TRACE, msg, *args, **kwargs)

    logger.trace = trace

    return logger


def adjust_log_level(logger, verbosity, *, quiet=False):

    if quiet:
        loglevel = logging.CRITICAL
    elif verbosity >= 3:
        loglevel = logging.DEBUG - verbosity + 3
    else:
        loglevel = logging.WARNING - verbosity * 10

    if loglevel <= logging.NOTSET:
        logger.warning("Log level at or below NOTSET")

    logger.setLevel(loglevel)


class LoggerAdapter(logging.LoggerAdapter):

    def trace(self, msg, *args, **kwargs):
        return self.log(logging.TRACE, msg, *args, **kwargs)

    def process(self, msg, kwargs):
        if extra := self.extra.get("id"):
            return f"[{extra}] {msg}", kwargs
        return msg, kwargs
