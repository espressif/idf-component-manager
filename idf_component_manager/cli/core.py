# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import sys
import warnings

import click

from idf_component_manager import version as idf_component_manager_version
from idf_component_manager.utils import CLICK_SUPPORTS_SHOW_DEFAULT, print_error, print_info
from idf_component_tools.errors import FatalError

from .autocompletion import autocomplete
from .cache import cache
from .component import component
from .manifest import manifest
from .project import project

try:
    from typing import Any
except ImportError:
    pass

DEFAULT_SETTINGS = {
    'help_option_names': ['-h', '--help'],
}  # type: dict[str, Any]

if CLICK_SUPPORTS_SHOW_DEFAULT:
    DEFAULT_SETTINGS['show_default'] = True


@click.group(context_settings=DEFAULT_SETTINGS)
@click.option('--warnings-as-errors', '-W', is_flag=True, default=False, help='Raise exception on warnings')
def cli(warnings_as_errors):
    if warnings_as_errors:
        warnings.filterwarnings('error', category=UserWarning)


@cli.command()
def version():
    """
    Print version of the IDF Component Manager
    """
    print_info(str(idf_component_manager_version))


cli.add_command(autocomplete)
cli.add_command(cache)
cli.add_command(component)
cli.add_command(manifest)
cli.add_command(project)


def safe_cli():
    """
    CLI entrypoint with error handling
    """
    try:
        cli()
    except UserWarning as e:
        print_error(e)
        sys.exit(1)
    except FatalError as e:
        print_error(e)
        sys.exit(e.exit_code)
