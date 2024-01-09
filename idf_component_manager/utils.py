# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import enum
import re

import click
from packaging import version

from idf_component_tools.messages import UserHint, UserNotice

CLICK_SUPPORTS_SHOW_DEFAULT = version.parse(click.__version__) >= version.parse('7.1.0')


def print_prefixed(
    prefix, color, message, stderr
):  # type: (str, str, Exception | str, bool) -> None
    styled_prefix = click.style('{}: '.format(prefix), fg=color)
    click.echo(styled_prefix + str(message), err=stderr)


def print_stderr_prefixed(prefix, color, message):  # type: (str, str, Exception | str) -> None
    print_prefixed(prefix, color, message, stderr=True)


def print_error(message):  # type: (Exception | str) -> None
    print_stderr_prefixed('ERROR', 'red', message)


def print_warn(message):  # type: (Exception | str) -> None
    print_stderr_prefixed('WARNING', 'yellow', message)


def print_hint(message):  # type: (Exception | str) -> None
    print_prefixed('HINT', 'yellow', message, stderr=False)


def print_notice(message):  # type: (Exception | str) -> None
    print_prefixed('NOTICE', 'green', message, stderr=False)


def showwarning(message, category, filename, lineno, file=None, line=None):
    if category is UserHint:
        print_hint(message)
    elif category is UserNotice:
        print_notice(message)
    else:
        print_warn(message)


def print_info(
    message,  # type: str
    fg=None,  # type: str | None
    bg=None,  # type: str | None
    bold=None,  # type: str | None
    underline=None,  # type: str | None
    blink=None,  # type: str | None
    **kwargs
):  # type: (...) -> None
    click.secho(message, fg=fg, bg=bg, bold=bold, underline=underline, blink=blink, **kwargs)


RE_PATTERN = type(re.compile(''))  # this is a workaround for `re.Pattern` for python<3.7


# total_ordering will raise an error in python 2.7 with enum34
#   ValueError: must define at least one ordering operation: < > <= >=
# The reason is that the `dir()` behavior is different,
# ___eq__, __lt__, __hash__ are not in the dir() result.
# define all six operators here
class ComponentSource(str, enum.Enum):
    # These double-quotes are coming from the build system
    IDF_COMPONENTS = '"idf_components"'
    PROJECT_MANAGED_COMPONENTS = '"project_managed_components"'
    PROJECT_EXTRA_COMPONENTS = '"project_extra_components"'
    PROJECT_COMPONENTS = '"project_components"'

    # the lower value is, the lower priority it is
    @classmethod
    def order(cls):
        return {
            cls.IDF_COMPONENTS: 0,
            cls.PROJECT_MANAGED_COMPONENTS: 1,
            cls.PROJECT_EXTRA_COMPONENTS: 2,
            cls.PROJECT_COMPONENTS: 3,
        }

    def __hash__(self):
        return hash(self.value)

    def __eq__(self, other):
        if not isinstance(other, ComponentSource):
            return NotImplemented

        return self.value == other.value

    def __ne__(self, other):
        if not isinstance(other, ComponentSource):
            return NotImplemented

        return self.value != other.value

    def __lt__(self, other):
        if not isinstance(other, ComponentSource):
            return NotImplemented

        return self.order()[self] < self.order()[other]

    def __le__(self, other):
        if not isinstance(other, ComponentSource):
            return NotImplemented

        return self < other or self == other

    def __gt__(self, other):
        if not isinstance(other, ComponentSource):
            return NotImplemented

        return not self <= other

    def __ge__(self, other):
        if not isinstance(other, ComponentSource):
            return NotImplemented

        return not self < other
