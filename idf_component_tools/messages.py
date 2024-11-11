# SPDX-FileCopyrightText: 2023-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0


from idf_component_tools import HINT_LEVEL, get_logger


class UserDeprecationWarning(DeprecationWarning):
    """Deprecation warning for user"""


def debug(message: str, *args, **kwargs) -> None:
    """Log in level 10 (DEBUG)"""
    logger = get_logger()
    logger.debug(message, *args, **kwargs)


def hint(message: str, *args, **kwargs) -> None:
    """Log in level 15"""
    logger = get_logger()
    logger.log(HINT_LEVEL, message, *args, **kwargs)


def notice(message: str, *args, **kwargs) -> None:
    """Log in level 20 (INFO)"""
    logger = get_logger()
    logger.info(message, *args, **kwargs)


def warn(message: str, *args, **kwargs) -> None:
    """Log in level 30 (WARNING)"""
    logger = get_logger()
    logger.warning(message, *args, **kwargs)


def error(message: str, *args, **kwargs) -> None:
    """Log in level 40 (ERROR)"""
    logger = get_logger()
    logger.error(message, *args, **kwargs)
