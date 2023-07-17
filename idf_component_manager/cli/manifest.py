# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import json

import click

from idf_component_manager.utils import print_info
from idf_component_tools.manifest.schemas import JSON_SCHEMA

from .constants import get_project_dir_option, get_service_profile_option
from .utils import add_options


def init_manifest():
    PROJECT_DIR_OPTION = get_project_dir_option()
    SERVICE_PROFILE_OPTION = get_service_profile_option()

    @click.group()
    def manifest():
        """
        Group of commands to manage manifest of the project.
        """
        pass

    @manifest.command()
    def schema():
        """
        Print json schema of the manifest file idf_component.yml
        """
        print_info(json.dumps(JSON_SCHEMA, indent=2))

    MANIFEST_OPTION = [
        click.option('--component', default='main', help='Component name in the project.'),
        click.option(
            '-p',
            '--path',
            default=None,
            help='Path to the component. The component name is ignored when the path is specified.',
        ),
    ]

    @manifest.command()
    @add_options(PROJECT_DIR_OPTION + MANIFEST_OPTION)
    def create(manager, component, path):
        """
        Create manifest file for the specified component.

        By default:

        If you run the command in the directory with project, the manifest
        will be created in the "main" directory.

        If you run the command in the directory with a component, the manifest
        will be created right in that directory.

        You can explicitly specify directory using the ``--path`` option.
        """
        manager.create_manifest(component=component, path=path)

    @manifest.command()
    @add_options(PROJECT_DIR_OPTION + SERVICE_PROFILE_OPTION + MANIFEST_OPTION)
    @click.argument('dependency', required=True)
    def add_dependency(manager, service_profile, component, path, dependency):
        """
        Add a dependency to the manifest file.

        By default:

        If you run the command in the directory with project, the dependency
        will be added to the manifest in the "main" directory.

        If you run the command in the directory with a component,
        the dependency will be added to the manifest right in that directory.

        You can explicitly specify directory using the ``--path`` option.

        \b
        Examples:
        - $ compote manifest add-dependency example/cmp
          Will add a component `example/cmp` with constraint `*`
        - $ compote manifest add-dependency example/cmp<=3.3.3
          Will add a component `example/cmp` with constraint `<=3.3.3`
        """
        manager.add_dependency(
            dependency, service_profile=service_profile, component=component, path=path
        )

    return manifest
