# SPDX-FileCopyrightText: 2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import warnings


class UserHint(Warning):
    pass


class UserNotice(Warning):
    pass


class MetadataWarning(UserHint):
    pass


class MetadataKeyWarning(MetadataWarning):
    def __init__(self, field_name, field_type):
        super(MetadataKeyWarning, self).__init__(
            'Unknown {} field "{}" in the manifest file'.format(field_type, field_name)
        )


class UserDeprecationWarning(UserWarning):
    pass


def warn(
    message,
):  # type: (Exception | str) -> None
    warnings.warn(str(message))


def hint(
    message,
):  # type: (Warning | Exception | str) -> None
    if isinstance(message, Warning):
        warnings.warn(message)
    else:
        warnings.warn(str(message), UserHint)


def notice(
    message,
):  # type: (Warning | Exception | str) -> None
    if isinstance(message, Warning):
        warnings.warn(message)
    else:
        warnings.warn(str(message), UserNotice)
