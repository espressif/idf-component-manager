# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import sys
import warnings

import click

from idf_component_manager import version as idf_component_manager_version
from idf_component_manager.utils import CLICK_SUPPORTS_SHOW_DEFAULT, print_error, print_info
from idf_component_tools.errors import FatalError

from .autocompletion import init_autocomplete
from .cache import init_cache
from .component import init_component
from .manifest import init_manifest
from .project import init_project
from .registry import init_registry

try:
    from typing import Any
except ImportError:
    pass

DEFAULT_SETTINGS = {
    'help_option_names': ['-h', '--help'],
}  # type: dict[str, Any]

if CLICK_SUPPORTS_SHOW_DEFAULT:
    DEFAULT_SETTINGS['show_default'] = True


def initialize_cli():
    """
    Initialize CLI
    """

    @click.group(context_settings=DEFAULT_SETTINGS)
    @click.option(
        '--warnings-as-errors', '-W', is_flag=True, default=False, help='Treat warnings as errors.'
    )
    def cli(warnings_as_errors):
        if warnings_as_errors:
            warnings.filterwarnings('error', category=UserWarning)

    @cli.command()
    def version():
        """
        Print version of the IDF Component Manager.
        """
        print_info(str(idf_component_manager_version))

    cli.add_command(init_autocomplete())
    cli.add_command(init_cache())
    cli.add_command(init_component())
    cli.add_command(init_manifest())
    cli.add_command(init_project())
    cli.add_command(init_registry())

    return cli


def safe_cli():
    """
    CLI entrypoint with error handling.
    """
    try:
        cli = initialize_cli()
        cli()
    except UserWarning as e:
        print_error(e)
        sys.exit(1)
    except FatalError as e:
        print_error(e)
        sys.exit(e.exit_code)
