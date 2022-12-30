# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import json

import click

from idf_component_manager.utils import print_info
from idf_component_tools.manifest.validator import manifest_json_schema

from .constants import PROJECT_DIR_OPTION
from .utils import add_options


@click.group()
def manifest():
    """
    Group of manifest related commands
    """
    pass


@manifest.command()
def schema():
    """
    Print json schema of the manifest file idf_component.yml
    """
    print_info(json.dumps(manifest_json_schema(), indent=2))


MANIFEST_COMPONENT_NAME_OPTION = [click.option('--component', default='main', help='Component name in the project')]


@manifest.command()
@add_options(PROJECT_DIR_OPTION + MANIFEST_COMPONENT_NAME_OPTION)
def create(manager, component):
    """
    Create manifest file for the specified component.
    """
    manager.create_manifest(component=component)


@manifest.command()
@add_options(PROJECT_DIR_OPTION + MANIFEST_COMPONENT_NAME_OPTION)
@click.argument('dependency', required=True)
def add_dependency(manager, component, dependency):
    """
    Add dependency to the manifest file. For now we only support adding dependencies from the component registry.

    \b
    Examples:
    - $ compote manifest add-dependency example/cmp
      would add component `example/cmp` with constraint `*`
    - $ compote manifest add-dependency example/cmp<=2.0.0
      would add component `example/cmp` with constraint `<=2.0.0`
    """
    manager.add_dependency(dependency, component=component)
