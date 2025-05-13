# SPDX-FileCopyrightText: 2022-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os
import subprocess  # noqa: S404
import typing as t

import click

from idf_component_tools.errors import FatalError
from idf_component_tools.semver import Version

CLI_NAME = 'compote'
CLICK_VERSION = Version.coerce(click.__version__)


def _get_shell_completion(shell: str) -> str:
    if CLICK_VERSION.major == 7:
        return 'source_' + shell
    elif CLICK_VERSION.major > 7:
        return shell + '_source'
    else:
        raise NotImplementedError


def _append_text_line(
    strings: t.Union[str, t.List[str]],
    filepath: str,
    write_string: t.Optional[str] = None,
    dry_run: bool = False,
) -> None:
    if isinstance(strings, str):
        strings = [strings]

    if not os.path.isfile(filepath):
        lines = []
    else:
        with open(filepath, encoding='utf8') as fr:
            lines = [line.rstrip('\n') for line in fr.readlines()]

    found = False
    for s in strings:
        if s in lines:
            found = True
            break

    if not found:
        if write_string is None:
            write_string = strings[-1]

        if dry_run:
            print(f'Would append the following line to {filepath}: {write_string}')
        else:
            with open(filepath, 'ab+') as fw:
                fw.write(f'\n{write_string}\n'.encode())


_COMPLETE_FILE_PATH = {
    'bash': f'~/.{CLI_NAME}-complete.bash',
    'zsh': f'~/.{CLI_NAME}-complete.zsh',
    'fish': f'~/.config/fish/completions/{CLI_NAME}.fish',
}

_RC_FILE_PATH = {
    'bash': '~/.bashrc',
    'zsh': '~/.zshrc',
    'fish': None,  # not needed
}

_SOURCING_STR = {
    'bash': f'. {_COMPLETE_FILE_PATH["bash"]}',
    'zsh': f'. {_COMPLETE_FILE_PATH["zsh"]}',
    'fish': None,  # not needed
}

_DOC_STRSTRING = """
    Generate tab-completion scripts for the specified shell.

    \b
    For BASH users, you may run:
        $ compote autocomplete --shell bash > {}
        $ echo "{}" >> {}

    \b
    For ZSH users, you may run:
        $ compote autocomplete --shell zsh > {}
        $ echo "{}" >> {}
    Or you may install the completion file into your $fpath.
    ~/.zfunc is a commonly used $fpath. You may run:
        $ compote autocomplete --shell zsh > ~/.zfunc/_compote

    \b
    For FISH users, completion files are commonly stored in {}. You may run:
        $ compote autocomplete --shell fish > {}

    For ALL users,
    you may have to log out and log in again to your shell session for the changes to take effect.

    \b
    Besides, you may use:
        $ compote autocomplete --shell [SHELL] --install
    to create the completion file and inject the sourcing script into your rc files automatically.

    \b
    You may also use:
        $ compote autocomplete --shell [SHELL] --install --dry-run
    to simulate running with the `--install` flag and check what would be done.
    """.format(
    _COMPLETE_FILE_PATH['bash'],
    _SOURCING_STR['bash'],
    _RC_FILE_PATH['bash'],
    _COMPLETE_FILE_PATH['zsh'],
    _SOURCING_STR['zsh'],
    _RC_FILE_PATH['zsh'],
    os.path.dirname(_COMPLETE_FILE_PATH['fish']),
    _COMPLETE_FILE_PATH['fish'],
)


def _doc(docstring):
    def wrapper(func):
        func.__doc__ = docstring
        return func

    return wrapper


def init_autocomplete():
    @click.command()
    @click.option(
        '--shell', required=True, type=click.Choice(['bash', 'zsh', 'fish']), help='Shell type'
    )
    @click.option(
        '--install',
        is_flag=True,
        default=False,
        help='Create the completion files and inject '
        'the sourcing script into your rc files if this flag is set.',
    )
    @click.option(
        '--dry-run',
        is_flag=True,
        default=False,
        help='Only useful when the flag "--install" is set. Instead of making real file system changes, '
        'logs will be printed if this flag is set.',
    )
    @_doc(_DOC_STRSTRING)
    def autocomplete(shell, install, dry_run):
        if shell == 'fish':
            if CLICK_VERSION < Version('7.1.0'):  # fish support was added in 7.1
                raise FatalError(
                    'Autocomplete for the fish shell is only supported by '
                    'library `click` version 7.1 and higher. An older version '
                    'is installed on your machine due to an outdated version of python. '
                    'We recommend using python 3.7 and higher with compote CLI.'
                )

        # the return code could be 1 even succeeded
        # use || true to swallow the return code
        autocomplete_script_str = subprocess.check_output(  # noqa: S602
            '_{}_COMPLETE={} {} || true'.format(
                CLI_NAME.upper(), _get_shell_completion(shell), CLI_NAME
            ),
            shell=True,
        ).decode('utf8')

        if not install:  # print the autocomplete script only
            print(autocomplete_script_str)
            return

        # write autocomplete script
        completion_filepath = os.path.realpath(os.path.expanduser(_COMPLETE_FILE_PATH[shell]))
        if not os.path.isdir(os.path.dirname(completion_filepath)):
            if not dry_run:
                os.makedirs(os.path.dirname(completion_filepath))

        if dry_run:
            print(f'Would create the completion file at: {completion_filepath}')
        else:
            with open(completion_filepath, 'w', encoding='utf-8') as fw:
                fw.write(autocomplete_script_str)

        # write sourcing autocomplete script statements
        if _RC_FILE_PATH[shell] and _SOURCING_STR[shell]:
            rc_filepath = os.path.realpath(os.path.expanduser(_RC_FILE_PATH[shell]))
            # enable zsh autocomplete
            if shell == 'zsh':
                _append_text_line('autoload -Uz compinit', rc_filepath, dry_run=dry_run)
                _append_text_line(['compinit', 'compinit -u'], rc_filepath, dry_run=dry_run)

            _append_text_line(
                '# ESP-IDF component manager compote CLI autocompletion\n{}'.format(
                    _SOURCING_STR[shell]
                ),
                rc_filepath,
                dry_run=dry_run,
            )

    return autocomplete
