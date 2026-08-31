# SPDX-FileCopyrightText: 2024-2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import typing as t
from contextlib import contextmanager

from esp_pylib.logger import EspLog, Verbosity

from idf_component_tools.environment import ComponentManagerSettings
from idf_component_tools.messages import configure_message_flags, debug


def _log_truststore_status() -> None:
    """Log truststore availability without claiming EspLog.instance.

    Injection stays at import in ``idf_component_manager.core``; this only
    re-checks importability for the debug line. Skip when no logger is
    installed yet so ``debug()`` cannot materialize a default EspLog.
    """
    if EspLog.instance is None:
        return
    try:
        import truststore  # noqa: F401
    except ImportError:
        debug(
            'Failed to import truststore, '
            "the 'certifi' package will be used as a source of trusted certificates"
        )
    else:
        debug('Use truststore as a source of trusted certificates')


@contextmanager
def suppress_logging(level: t.Optional[int] = None):  # type: ignore[return]
    """Suppress logging temporarily by switching to SILENT verbosity.

    ``level`` is accepted only for backwards compatibility with the previous
    stdlib-``logging`` implementation and is ignored: esp-pylib models only
    SILENT/NORMAL/VERBOSE, so suppression is always full.
    """
    del level  # accepted for backwards compatibility; intentionally ignored
    instance = EspLog.instance
    if instance is None:
        yield
        return
    previous = instance._verbosity  # type: ignore[attr-defined]
    instance.set_verbosity(Verbosity.SILENT)
    try:
        yield
    finally:
        instance.set_verbosity(previous)


def setup_logging(warnings_as_errors: bool = False) -> None:
    """Install and configure the process logger when component manager is the app.

    Call only from CLI / prepare_components entry points — never from idf.py
    extension registration (use ``configure_extension_logging`` there).
    """
    settings = ComponentManagerSettings()
    configure_message_flags(
        no_hints=settings.NO_HINTS and not settings.DEBUG_MODE,
        warnings_as_errors=warnings_as_errors,
    )
    # Clear the active slot so EspLog() constructs a fresh instance. EspLog.__new__
    # returns whatever is already in EspLog.instance (including foreign loggers),
    # so we must empty the slot before claiming ownership. Avoid EspLog._reset()
    # (documented for tests only).
    EspLog.instance = None
    instance = EspLog(no_color=settings.NO_COLORS or None)
    instance.set_verbosity(Verbosity.VERBOSE if settings.DEBUG_MODE else Verbosity.NORMAL)
    EspLog.set_logger(instance)
    _log_truststore_status()


def configure_extension_logging() -> None:
    """Apply component-manager message policy without owning EspLog.instance.

    Used from idf.py ``action_extensions()`` so CM does not hijack the host
    process logger (colour / verbosity / singleton type stay with idf.py).
    """
    settings = ComponentManagerSettings()
    configure_message_flags(
        no_hints=settings.NO_HINTS and not settings.DEBUG_MODE,
        warnings_as_errors=False,
    )
    _log_truststore_status()
