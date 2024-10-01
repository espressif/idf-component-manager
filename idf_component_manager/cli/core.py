# SPDX-FileCopyrightText: 2022-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import sys
import typing as t

import click

from idf_component_manager.utils import (
    CLICK_SUPPORTS_SHOW_DEFAULT,
)
from idf_component_tools import error, setup_logging
from idf_component_tools.__version__ import __version__ as idf_component_manager_version
from idf_component_tools.errors import FatalError, WarningAsExceptionError

from .autocompletion import init_autocomplete
from .cache import init_cache
from .component import init_component
from .config import init_config
from .manifest import init_manifest
from .project import init_project
from .registry import init_registry

DEFAULT_SETTINGS: t.Dict[str, t.Any] = {
    'help_option_names': ['-h', '--help'],
}

if CLICK_SUPPORTS_SHOW_DEFAULT:
    DEFAULT_SETTINGS['show_default'] = True


def initialize_cli():
    """
    Initialize the CLI.
    """

    @click.group(context_settings=DEFAULT_SETTINGS)
    @click.option(
        '--warnings-as-errors',
        '-W',
        is_flag=True,
        default=False,
        help='Treat warnings as errors.',
    )
    def cli(warnings_as_errors):
        setup_logging(warnings_as_errors)

    @cli.command()
    def version():
        """
        Print the version of the IDF Component Manager.
        """
        print(idf_component_manager_version)

    cli.add_command(init_autocomplete())
    cli.add_command(init_cache())
    cli.add_command(init_component())
    cli.add_command(init_manifest())
    cli.add_command(init_project())
    cli.add_command(init_registry())
    cli.add_command(init_config())

    return cli


def safe_cli():
    """
    CLI entry point with error handling.
    """
    try:
        cli = initialize_cli()
        cli()
    except WarningAsExceptionError as e:
        error(str(e))
        sys.exit(1)
    except FatalError as e:
        error(str(e))
        sys.exit(e.exit_code)
