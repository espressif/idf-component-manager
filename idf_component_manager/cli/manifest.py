# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import json

import click

from idf_component_tools.manifest import MANIFEST_JSON_SCHEMA

from .constants import get_profile_option, get_project_dir_option
from .utils import add_options


def init_manifest():
    PROJECT_DIR_OPTION = get_project_dir_option()
    PROFILE_OPTION = get_profile_option()

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
        print(json.dumps(MANIFEST_JSON_SCHEMA, indent=2))

    MANIFEST_OPTIONS = [
        click.option('--component', default='main', help='Component name in the project.'),
        click.option(
            '-p',
            '--path',
            default=None,
            help='Path to the component. The component name is ignored when the path is specified.',
        ),
    ]

    GIT_OPTIONS = [
        click.option('--git', default=None, help='Git URL of the component.'),
        click.option(
            '--git-path', default='.', help='Path to the component in the git repository.'
        ),
        click.option(
            '--git-ref',
            default=None,
            help='Git reference (branch, tag, commit SHA) of the component.',
        ),
    ]

    @manifest.command()
    @add_options(PROJECT_DIR_OPTION + MANIFEST_OPTIONS)
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
    @add_options(PROJECT_DIR_OPTION + PROFILE_OPTION + MANIFEST_OPTIONS + GIT_OPTIONS)
    @click.argument('dependency', required=True)
    def add_dependency(manager, profile_name, component, path, dependency, git, git_path, git_ref):
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
            dependency,
            profile_name=profile_name,
            component=component,
            path=path,
            git=git,
            git_path=git_path,
            git_ref=git_ref,
        )

    return manifest
