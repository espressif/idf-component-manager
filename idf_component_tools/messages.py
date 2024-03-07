# SPDX-FileCopyrightText: 2023-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import warnings
from typing import Union


class UserHint(Warning):
    pass


class UserNotice(Warning):
    pass


class MetadataWarning(UserHint):
    pass


class MetadataKeyWarning(MetadataWarning):
    def __init__(self, field_name, field_type):
        super().__init__(f'Unknown {field_type} field "{field_name}" in the manifest file')


class UserDeprecationWarning(UserWarning):
    pass


def warn(
    message: Union[Exception, str],
) -> None:
    warnings.warn(str(message))


def hint(message: Union[Warning, Exception, str]) -> None:
    if isinstance(message, Warning):
        warnings.warn(message)
    else:
        warnings.warn(str(message), UserHint)


def notice(message: Union[Warning, Exception, str]) -> None:
    if isinstance(message, Warning):
        warnings.warn(message)
    else:
        warnings.warn(str(message), UserNotice)
