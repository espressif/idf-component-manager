# SPDX-FileCopyrightText: 2022-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import click

from idf_component_manager.cli.validations import validate_path_for_project

from .constants import get_project_dir_option, get_project_options
from .utils import add_options


def init_project():
    PROJECT_DIR_OPTION = get_project_dir_option()
    PROJECT_OPTIONS = get_project_options()

    @click.group()
    def project():
        """
        Group of project-related commands.
        """
        pass

    @project.command()
    @add_options(PROJECT_OPTIONS)
    @click.option(
        '-p',
        '--path',
        default=None,
        help='Path to the new project. '
        'The project will be created directly in the given folder if it is empty.',
        callback=validate_path_for_project,
    )
    @click.argument('example', required=True)
    def create_from_example(manager, example, path, profile_name):
        """
        Create a project from an example.

        You can specify EXAMPLE in the following format:
        namespace/name=1.0.0:example

        where "=1.0.0" is a version specification.

        An example command:

        compote project create-from-example example/cmp^3.3.8:cmp_ex

        The namespace and version are optional in the EXAMPLE argument.
        """
        manager.create_project_from_example(example, path=path, profile_name=profile_name)

    @project.command()
    @add_options(PROJECT_DIR_OPTION)
    def remove_managed_components(manager):
        """
        Remove the managed_components folder.
        """
        manager.remove_managed_components()

    return project
