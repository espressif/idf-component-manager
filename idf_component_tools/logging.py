# SPDX-FileCopyrightText: 2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import logging
import sys
from contextlib import contextmanager

from colorama import Fore

from idf_component_tools import HINT_LEVEL, get_logger
from idf_component_tools.environment import ComponentManagerSettings
from idf_component_tools.errors import WarningAsExceptionError


class ComponentManagerStdoutFilter(logging.Filter):
    """
    In component manager, we write debug, hint, info to stdout
    """

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno < logging.WARNING


class ComponentManagerStderrFilter(logging.Filter):
    """
    In component manager, we write warning, error, critical to stderr
    """

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno >= logging.WARNING


class ComponentManagerWarningsAsErrorsFilter(logging.Filter):
    """
    Treat warnings as errors with exception when -W flag is passed.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno == logging.WARNING:
            raise WarningAsExceptionError(record.msg)

        return True


class ComponentManagerFormatter(logging.Formatter):
    """
    In component manager, we have the following logging levels

    -  10 -> debug
    -  15 -> hint (custom level, default)
    -  20 -> info (notice)
    -  30 -> warning
    -  40 -> error
    -  50 -> critical
    """

    fmt: str = '%(message)s'

    PREFIX = {
        logging.DEBUG: 'DEBUG',
        HINT_LEVEL: 'HINT',
        logging.INFO: 'NOTICE',
        logging.WARNING: 'WARNING',
        logging.ERROR: 'ERROR',
        logging.CRITICAL: 'FATAL',
    }

    COLOR = {
        logging.DEBUG: Fore.LIGHTBLACK_EX,
        HINT_LEVEL: Fore.CYAN,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED,
    }

    def __init__(self, colored: bool = True) -> None:
        self.colored = colored

        super().__init__(fmt=self.fmt)

    def format(self, record: logging.LogRecord) -> str:
        if self.colored and sys.stdout.isatty() and sys.stderr.isatty():
            record.msg = f'{self.COLOR[record.levelno]}{self.PREFIX[record.levelno]}: {record.msg}{Fore.RESET}'
        else:
            record.msg = f'{self.PREFIX[record.levelno]}: {record.msg}'
        return super().format(record)


@contextmanager
def suppress_logging(level: int = logging.CRITICAL):
    """Suppress logging temporarily"""
    previous = get_logger().getEffectiveLevel()

    logging.disable(level)

    try:
        yield
    finally:
        logging.disable(previous)


def setup_logging(warnings_as_errors: bool = False) -> None:
    """setup logger for the component manager"""
    logger = get_logger()

    if ComponentManagerSettings().DEBUG_MODE:
        logger.setLevel(logging.DEBUG)
    elif ComponentManagerSettings().NO_HINTS:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(HINT_LEVEL)

    # cleanup first
    logger.handlers.clear()

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.addFilter(ComponentManagerStdoutFilter())
    stdout_handler.setFormatter(
        ComponentManagerFormatter(colored=(not ComponentManagerSettings().NO_COLORS))
    )
    logger.addHandler(stdout_handler)

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.addFilter(ComponentManagerStderrFilter())
    stderr_handler.setFormatter(
        ComponentManagerFormatter(colored=(not ComponentManagerSettings().NO_COLORS))
    )
    logger.addHandler(stderr_handler)

    if warnings_as_errors:
        stderr_handler.addFilter(ComponentManagerWarningsAsErrorsFilter())

    logger.propagate = False  # ends here, don't propagate to root logger, we're client code
