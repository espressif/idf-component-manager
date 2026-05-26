# SPDX-FileCopyrightText: 2023-2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

from esp_pylib.logger import log
from rich.markup import escape


class UserDeprecationWarning(DeprecationWarning):
    """Deprecation warning for user"""


def _fmt(message: str, args: tuple) -> str:
    """Collapse %-style lazy format args into a pre-formatted string for esp-pylib.

    esp-pylib renders messages as Rich markup and does not escape, so any ``[...]``
    in the text (paths, version specs, wrapped exception messages) would be parsed
    as a markup tag -- silently dropped, or raising ``rich.errors.MarkupError`` for
    malformed tags like ``[/]``.  The pre-migration stdlib logger treated messages
    as plain text, so we escape here to keep that behaviour.
    """
    formatted = message % args if args else message
    # Only strings carry markup; pass anything else (e.g. None) through untouched,
    # as the pre-escape code did, so callers relying on that aren't broken.
    return escape(formatted) if isinstance(formatted, str) else formatted


def debug(message: str, *args, **kwargs) -> None:
    """Log at debug level (dim, verbose-only).

    ``**kwargs`` are accepted for backwards compatibility with stdlib logging call sites
    (e.g. ``exc_info=``, ``stacklevel=``, ``extra=``).  They are silently ignored because
    esp-pylib's log API has no equivalent — only for backwards compatibility with callers
    that passed these kwargs before the esp-pylib migration.
    """
    log.debug(_fmt(message, args))


def hint(message: str, *args, **kwargs) -> None:
    """Log a hint (suppressible via NO_HINTS=1).

    ``**kwargs`` are accepted for backwards compatibility — see ``debug`` for details.
    """
    log.hint(_fmt(message, args))


def notice(message: str, *args, **kwargs) -> None:
    """Log an informational note.

    ``**kwargs`` are accepted for backwards compatibility — see ``debug`` for details.
    """
    log.note(_fmt(message, args))


def warn(message: str, *args, **kwargs) -> None:
    """Log a warning.

    ``**kwargs`` are accepted for backwards compatibility — see ``debug`` for details.
    """
    log.warn(_fmt(message, args))


def error(message: str, *args, **kwargs) -> None:
    """Log an error.

    ``**kwargs`` are accepted for backwards compatibility — see ``debug`` for details.
    """
    log.err(_fmt(message, args))
