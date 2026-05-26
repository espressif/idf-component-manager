# SPDX-FileCopyrightText: 2024-2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import logging as lib_logging

from idf_component_tools.environment import ComponentManagerSettings
from idf_component_tools.logging import setup_logging
from idf_component_tools.messages import (
    debug,
    error,
    hint,
    notice,
    warn,
)

LOGGING_NAMESPACE = __package__
HINT_LEVEL = 15


def get_logger() -> lib_logging.Logger:
    """Return the stdlib logger for the component manager namespace.

    Kept for backwards compatibility with external importers. Component-manager
    output now flows through esp-pylib (``EspLog``); this stdlib logger is no
    longer that output channel, so it behaves as a plain
    ``logging.getLogger('idf_component_tools')``.
    """
    return lib_logging.getLogger(LOGGING_NAMESPACE)


__all__ = [
    'ComponentManagerSettings',
    'debug',
    'error',
    'get_logger',
    'hint',
    'notice',
    'setup_logging',
    'warn',
]
