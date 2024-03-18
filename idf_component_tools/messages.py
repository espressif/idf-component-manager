# SPDX-FileCopyrightText: 2023-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import typing as t
import warnings


class UserHint(Warning):
    pass


class UserNotice(Warning):
    pass


class MetadataWarning(UserHint):
    pass


class UserDeprecationWarning(UserWarning):
    pass


def warn(
    message: t.Union[Exception, str],
) -> None:
    warnings.warn(str(message))


def hint(message: t.Union[Warning, Exception, str]) -> None:
    if isinstance(message, Warning):
        warnings.warn(message)
    else:
        warnings.warn(str(message), UserHint)


def notice(message: t.Union[Warning, Exception, str]) -> None:
    if isinstance(message, Warning):
        warnings.warn(message)
    else:
        warnings.warn(str(message), UserNotice)
