# SPDX-FileCopyrightText: 2024-2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import typing as t
from contextlib import contextmanager

from esp_pylib.logger import EspLog, Verbosity

from idf_component_tools.environment import ComponentManagerSettings
from idf_component_tools.errors import WarningAsExceptionError


class ComponentManagerLog(EspLog):
    """
    EspLog subclass for the IDF Component Manager.

    Adds two component-manager-specific flags:
      _no_hints:            suppresses hint() output (set from NO_HINTS env var).
      _warnings_as_errors:  when set, warn() raises WarningAsExceptionError.
    """

    _no_hints: bool = False
    _warnings_as_errors: bool = False

    def warn(self, message: str, suggestion: t.Optional[str] = None) -> None:
        if self._warnings_as_errors:
            raise WarningAsExceptionError(message)
        super().warn(message, suggestion=suggestion)

    def hint(self, message: str) -> None:
        """esp-pylib hint(), suppressible via NO_HINTS=1."""
        if not self._no_hints:
            super().hint(message)


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
    """Set up the component manager logger as the global esp-pylib singleton."""
    settings = ComponentManagerSettings()
    EspLog._reset()
    ComponentManagerLog._reset()
    instance = ComponentManagerLog(no_color=settings.NO_COLORS or None)
    instance._no_hints = settings.NO_HINTS and not settings.DEBUG_MODE
    instance._warnings_as_errors = warnings_as_errors
    instance.set_verbosity(Verbosity.VERBOSE if settings.DEBUG_MODE else Verbosity.NORMAL)
    EspLog.set_logger(instance)
