# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import click

from .constants import get_project_dir_option, get_project_options
from .utils import add_options


def init_project():
    PROJECT_DIR_OPTION = get_project_dir_option()
    PROJECT_OPTIONS = get_project_options()

    @click.group()
    def project():
        """
        Group of project related commands
        """
        pass

    @project.command()
    @add_options(PROJECT_OPTIONS)
    @click.option(
        '-p',
        '--path',
        default=None,
        help='Path of the new project. '
        'The project will be created directly in the given folder if it is empty.',
    )
    @click.argument('example', required=True)
    def create_from_example(manager, example, path, service_profile):
        """
        Create a project from an example.

        You can specify EXAMPLE in the format like:
        namespace/name=1.0.0:example

        where "=1.0.0" is a version specification.

        An example command:

        compote project create-from-example example/cmp^3.3.8:cmp_ex

        Namespace and version are optional in the EXAMPLE argument.
        """
        manager.create_project_from_example(example, path=path, service_profile=service_profile)

    @project.command()
    @add_options(PROJECT_DIR_OPTION)
    def remove_managed_components(manager):
        """
        Remove the managed_components folder.
        """
        manager.remove_managed_components()

    return project
