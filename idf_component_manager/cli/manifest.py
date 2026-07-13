# SPDX-FileCopyrightText: 2022-2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import json
import os

import rich_click as click

from idf_component_manager.cli.validations import (
    validate_add_dependency,
    validate_existing_dir,
    validate_git_url,
    validate_url,
)
from idf_component_manager.core import ComponentManager
from idf_component_tools.manifest import MANIFEST_JSON_SCHEMA

from .constants import get_profile_option, get_project_dir_option
from .utils import add_options


def init_manifest():
    PROJECT_DIR_OPTION = get_project_dir_option()
    PROFILE_OPTION = get_profile_option()

    @click.group()
    def manifest():
        """
        Group of commands for managing the project manifest.
        """
        pass

    @manifest.command()
    def schema():
        """
        Print the JSON schema of the manifest file idf_component.yml.
        """
        print(json.dumps(MANIFEST_JSON_SCHEMA, indent=2))

    MANIFEST_OPTIONS = [
        click.option(
            '--component',
            default='main',
            help='Name of the component in the project where the dependency will be added.',
        ),
        click.option(
            '-p',
            '--path',
            default=None,
            help='Path to the component where the dependency will be added. The component name is ignored if the path is specified.',
            callback=validate_existing_dir,
        ),
    ]

    GIT_OPTIONS = [
        click.option(
            '--git',
            default=None,
            help='Git URL of the component.',
            callback=validate_git_url,
        ),
        click.option(
            '--git-path', default='.', help='Path to the component in the Git repository.'
        ),
        click.option(
            '--git-ref',
            default=None,
            help='Git reference (branch, tag, or commit SHA) of the component.',
        ),
    ]

    @manifest.command()
    @add_options(PROJECT_DIR_OPTION + MANIFEST_OPTIONS)
    def create(manager, component, path):
        """
        Create a manifest file for the specified component.

        By default:

        - If you run the command in a project directory, the manifest will be created in the "main" directory.
        - If you run the command in a component directory, the manifest will be created in that directory.

        You can explicitly specify a directory using the ``--path`` option.
        """
        manager.create_manifest(component=component, path=path)

    @manifest.command()
    @click.argument('paths', nargs=-1, type=click.Path())
    def lint(paths):
        """
        Validate manifest files (idf_component.yml) without modifying them.

        Works like a standard linter:

        \b
        - With no PATHS, every manifest under the current directory is validated.
        - A PATH that is a file validates that manifest directly.
        - A PATH that is a directory validates every manifest found under it.

        Valid manifests produce no output. The command exits with a non-zero status
        code if any manifest is invalid.

        This command intentionally accepts only positional PATHS; it does not
        support the --component or --path options used by other manifest commands.

        \b
        Examples:
        - $ compote manifest lint
          Validate every manifest under the current directory.
        - $ compote manifest lint components/foo
          Validate every manifest under "components/foo".
        - $ compote manifest lint components/foo/idf_component.yml
          Validate a single manifest file.
        """
        ComponentManager(os.getcwd()).lint_manifest(paths=paths)

    @manifest.command()
    @add_options(
        PROJECT_DIR_OPTION
        + PROFILE_OPTION
        + MANIFEST_OPTIONS
        + GIT_OPTIONS
        + [
            click.option(
                '--registry-url',
                default=None,
                help='URL of the registry.',
                callback=validate_url,
            )
        ]
    )
    @click.argument('dependency', required=True, callback=validate_add_dependency)
    def add_dependency(
        manager, profile_name, component, path, dependency, registry_url, git, git_path, git_ref
    ):
        """
        Add a dependency to the manifest file.

        By default:

        - If you run the command in a project directory, the dependency will be added to the manifest in the "main" directory.
        - If you run the command in a component directory, the dependency will be added to the manifest in that directory.

        You can explicitly specify a directory using the ``--path`` option.

        \b
        Examples:
        - $ compote manifest add-dependency example/cmp
          Will add a component `example/cmp` with the constraint `*`.
        - $ compote manifest add-dependency example/cmp<=3.3.3
          Will add a component `example/cmp` with the constraint `<=3.3.3`.
        - $ compote manifest add-dependency example/cmp --registry-url https://components-staging.espressif.com
          Will add a component `example/cmp` from the staging registry with the constraint `*`.
        - $ compote manifest add-dependency cmp --git https://github.com/espressif/example_components.git --git-path cmp
          Will add a component `cmp` from the Git repository with the path `cmp`.

        """
        manager.add_dependency(
            dependency,
            profile_name=profile_name,
            component=component,
            path=path,
            registry_url=registry_url,
            git=git,
            git_path=git_path,
            git_ref=git_ref,
        )

    return manifest
