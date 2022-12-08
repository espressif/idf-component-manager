# SPDX-FileCopyrightText: 2022 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import click
from packaging import version

from idf_component_tools.errors import UserHint

try:
    from typing import Any
except ImportError:
    pass

CLICK_SUPPORTS_SHOW_DEFAULT = version.parse(click.__version__) >= version.parse('7.1.0')


def print_stderr_prefixed(prefix, color, message):  # type: (str, str, Exception | str) -> None
    styled_prefix = click.style('{}: '.format(prefix), fg=color)
    click.echo(styled_prefix + str(message), err=True)


def print_error(message):  # type: (Exception | str) -> None
    print_stderr_prefixed('ERROR', 'red', message)


def print_warn(message):  # type: (Exception | str) -> None
    print_stderr_prefixed('WARNING', 'yellow', message)


def print_hint(message):  # type: (Exception | str) -> None
    print_stderr_prefixed('HINT', 'yellow', message)


def showwarning(message, category, filename, lineno, file=None, line=None):
    if category is UserHint:
        print_hint(message)
    else:
        print_warn(message)


def print_info(
        message,  # type: str
        fg=None,  # type: str | None
        bg=None,  # type: str | None
        bold=None,  # type: str | None
        underline=None,  # type: str | None
        blink=None,  # type: str | None
        **kwargs  # type: 'Any'
):  # type: (...) -> None
    click.secho(message, fg=fg, bg=bg, bold=bold, underline=underline, blink=blink, **kwargs)
