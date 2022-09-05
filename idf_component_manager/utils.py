# SPDX-FileCopyrightText: 2022 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import click

try:
    from typing import Any
except ImportError:
    pass


def print_stderr_prefixed(prefix, color, message):  # type: (str, str, Exception | str) -> None
    styled_prefix = click.style('{}: '.format(prefix), fg=color)
    click.echo(styled_prefix + str(message), err=True)


def error(message):  # type: (Exception | str) -> None
    print_stderr_prefixed('ERROR', 'red', message)


def warn(message):  # type: (Exception | str) -> None
    print_stderr_prefixed('WARNING', 'yellow', message)


def info(
        message,  # type: str
        fg=None,  # type: str | None
        bg=None,  # type: str | None
        bold=None,  # type: str | None
        underline=None,  # type: str | None
        blink=None,  # type: str | None
        **kwargs  # type: 'Any'
):  # type: (...) -> None
    click.secho(message, fg=fg, bg=bg, bold=bold, underline=underline, blink=blink, **kwargs)
