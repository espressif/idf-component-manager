# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os
import subprocess  # nosec
from io import open

import click

from idf_component_tools.errors import FatalError
from idf_component_tools.semver import Version

CLI_NAME = 'compote'


@click.command()
@click.option('--shell', required=True, type=click.Choice(['bash', 'zsh', 'fish']), help='Shell type')
def autocomplete(shell):
    """
    Inject sourcing of the autocomplete script into your shell configuration

    \b
    Examples:
    - $ compote autocomplete --shell zsh
      would inject sourcing of the autocomplete script into your .zshrc config.
      run `exec zsh` afterwards would make it work for your current terminal.
    """
    click_version = Version.coerce(click.__version__)

    if shell == 'fish':
        if click_version < Version('7.1.0'):  # fish support was added in 7.1
            raise FatalError(
                'Autocomplete for the fish shell is only supported by library `click` version 7.1 and higher. '
                'An older version is installed on your machine due to an outdated version of python. '
                'We recommend using python 3.7 and higher with compote CLI.')

    def get_shell_completion():
        if click_version.major == 7:
            return 'source_' + shell
        elif click_version.major > 7:
            return shell + '_source'
        else:
            raise NotImplementedError

    def add_if_not_exist(strings, filepath, write_string=None):  # type: (str | list[str], str, str | None) -> None
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

            with open(filepath, 'ab+') as fw:
                fw.write('\n{}\n'.format(write_string).encode('utf8'))

    if shell == 'bash':
        complete_filepath = '~/.{}-complete.bash'.format(CLI_NAME)
        shell_str = '_{}_COMPLETE={} {} > {}'.format(
            CLI_NAME.upper(), get_shell_completion(), CLI_NAME, complete_filepath)
        config_filepath = '~/.bashrc'
        config_str = '. {}'.format(complete_filepath)
    elif shell == 'zsh':
        complete_filepath = '~/.{}-complete.zsh'.format(CLI_NAME)
        shell_str = '_{}_COMPLETE={} {} > {}'.format(
            CLI_NAME.upper(), get_shell_completion(), CLI_NAME, complete_filepath)
        config_filepath = '~/.zshrc'
        config_str = '. {}'.format(complete_filepath)
    else:  # fish
        complete_filepath = '~/.config/fish/completions/{}.fish'.format(CLI_NAME)
        shell_str = '_{}_COMPLETE={} {} > {}'.format(
            CLI_NAME.upper(), get_shell_completion(), CLI_NAME, complete_filepath)
        config_filepath = ''
        config_str = ''

    if config_filepath and config_str:
        config = os.path.expanduser(config_filepath)
        # zsh autocomplete
        if shell == 'zsh':
            add_if_not_exist('autoload -Uz compinit', config)
            add_if_not_exist(['compinit', 'compinit -u'], config)

        add_if_not_exist(config_str, config)

    complete_file = os.path.expanduser(complete_filepath)
    if not os.path.isdir(os.path.dirname(complete_file)):
        os.makedirs(os.path.dirname(complete_file))

    subprocess.call(shell_str, shell=True)  # nosec
