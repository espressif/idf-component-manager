# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import re

import click
from packaging import version

from idf_component_tools.messages import UserHint, UserNotice

CLICK_SUPPORTS_SHOW_DEFAULT = version.parse(click.__version__) >= version.parse('7.1.0')


def print_prefixed(
    prefix, color, message, stderr=True
):  # type: (str, str, Exception | str, bool) -> None
    styled_prefix = click.style('{}: '.format(prefix), fg=color)
    click.echo(styled_prefix + str(message), err=stderr)


def print_error(message):  # type: (Exception | str) -> None
    print_prefixed('ERROR', 'red', message)


def print_warn(message):  # type: (Exception | str) -> None
    print_prefixed('WARNING', 'yellow', message)


def print_hint(message):  # type: (Exception | str) -> None
    print_prefixed('HINT', 'yellow', message)


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
