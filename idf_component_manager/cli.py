# SPDX-FileCopyrightText: 2022 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os
import subprocess  # nosec

import click

CLI_NAME = 'compote'


@click.group()
def cli():
    pass


@cli.command()
@click.option('--shell', required=True, type=click.Choice(['bash', 'zsh', 'fish']))
def autocomplete(shell):
    if shell == 'bash':
        complete_filepath = '~/.{}-complete.bash'.format(CLI_NAME)
        shell_str = '_{}_COMPLETE=bash_source {} > {}'.format(CLI_NAME.upper(), CLI_NAME, complete_filepath)
        config_filepath = '~/.bashrc'
        config_str = '. {}'.format(complete_filepath)
    elif shell == 'zsh':
        complete_filepath = '~/.{}-complete.zsh'.format(CLI_NAME)
        shell_str = '_{}_COMPLETE=zsh_source {} > {}'.format(CLI_NAME.upper(), CLI_NAME, complete_filepath)
        config_filepath = '~/.zshrc'
        config_str = '. {}'.format(complete_filepath)
    else:  # fish
        complete_filepath = '~/.config/fish/completions/{}.fish'.format(CLI_NAME)
        shell_str = '_{}_COMPLETE=fish_source {} > {}'.format(CLI_NAME.upper(), CLI_NAME, complete_filepath)
        config_filepath = ''
        config_str = ''

    if config_filepath and config_str:
        config = os.path.expanduser(config_filepath)
        if not os.path.isfile(config):
            s = ''
        else:
            with open(config, 'r') as fr:
                s = fr.read()

        if config_str not in s:
            with open(config, 'a+') as fw:
                fw.write('\n{}\n'.format(config_str))

    complete_file = os.path.expanduser(complete_filepath)
    if not os.path.isdir(os.path.dirname(complete_file)):
        os.makedirs(os.path.dirname(complete_file))

    subprocess.run(shell_str, shell=True)  # nosec
