# SPDX-FileCopyrightText: 2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import logging as lib_logging

LOGGING_NAMESPACE = __package__
HINT_LEVEL = 15


def get_logger() -> lib_logging.Logger:
    """
    Get logger for the component manager.

    Use this instead of `logging.getLogger(__package__)` to get the universal logger for both
    component_manager and component_tools
    """
    return lib_logging.getLogger(LOGGING_NAMESPACE)


from idf_component_tools.environment import ComponentManagerSettings  # noqa: E402
from idf_component_tools.logging import setup_logging  # noqa: E402
from idf_component_tools.messages import (  # noqa: E402
    debug,
    error,
    hint,
    notice,
    warn,
)

__all__ = [
    'ComponentManagerSettings',
    'debug',
    'error',
    'get_logger',
    'hint',
    'notice',
    'setup_logging',
    'warn',
    'debug',
    'error',
]
