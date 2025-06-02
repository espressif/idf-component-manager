# SPDX-FileCopyrightText: 2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import re
from pathlib import Path
from urllib.parse import urlparse

import click

from idf_component_manager.core_utils import COMPONENT_FULL_NAME_WITH_SPEC_REGEX
from idf_component_tools.archive_tools import ArchiveError, get_format_from_path
from idf_component_tools.constants import COMPILED_COMMIT_ID_RE, COMPILED_GIT_URL_RE
from idf_component_tools.manifest import WEB_DEPENDENCY_REGEX
from idf_component_tools.manifest.constants import SLUG_REGEX
from idf_component_tools.semver import Version
from idf_component_tools.semver.base import SimpleSpec


def validate_name(ctx, param, value):  # noqa: ARG001
    if value is not None:
        name = value.lower()

        if not re.match(SLUG_REGEX, name):
            raise click.BadParameter(
                f'"{name}" should consist of 2 or more letters, numbers, "-" or "_". '
                'It cannot start or end with "_" or "-", or have sequences of these characters.'
            )
        return name


def validate_existing_dir(ctx, param, value):  # noqa: ARG001
    if value is not None:
        if not value or not Path(value).is_dir():
            raise click.BadParameter(f'"{value}" directory does not exist.')
    return value


def validate_url(ctx, param, value):  # noqa: ARG001
    if value:
        result = urlparse(value)
        if not result.scheme or not result.hostname:
            raise click.BadParameter('Invalid URL.')
    return value


def validate_sha(ctx, param, value):  # noqa: ARG001
    if value is not None and not COMPILED_COMMIT_ID_RE.match(value):
        raise click.BadParameter('Invalid SHA-1 hash.')
    return value


def validate_git_url(ctx, param, value):  # noqa: ARG001
    if value is not None and not COMPILED_GIT_URL_RE.match(value):
        raise click.BadParameter('Invalid Git remote URL.')
    return value


def validate_path_for_project(ctx, param, value):  # noqa: ARG001
    if value is not None:
        project_path = Path(value)
        if project_path.is_file():
            raise click.BadParameter(
                f'Your target path is not a directory. '
                f'Please remove the {project_path.resolve()} or use a different target path.'
            )

        if project_path.is_dir() and any(project_path.iterdir()):
            raise click.BadParameter(
                f'The directory "{project_path}" is not empty. '
                'To create an example you must empty the directory or '
                'choose a different path.',
            )
    return value


def validate_if_archive(ctx, param, value):  # noqa: ARG001
    if value is not None:
        if not Path(value).is_file():
            raise click.BadParameter(
                f'Cannot find archive to upload: {value}. Please check the path or if it exists.'
            )
        try:
            get_format_from_path(value)
        except ArchiveError:
            raise click.BadParameter(f'Unknown archive extension for file: {value}')
    return value


def validate_version(ctx, param, value):  # noqa: ARG001
    if value is not None:
        try:
            Version.parse(value)
        except ValueError:
            raise click.BadParameter(
                f'Invalid version scheme.\n'
                f'Received: "{value}"\n'
                'Documentation: https://docs.espressif.com/projects/idf-component-manager/en/'
                'latest/reference/versioning.html#versioning-scheme'
            )
    return value


def validate_registry_component(ctx, param, value):  # noqa: ARG001
    if value is not None:
        for component in value:
            match = re.match(COMPONENT_FULL_NAME_WITH_SPEC_REGEX, component)
            if not match:
                raise click.BadParameter(
                    'Cannot parse COMPONENT argument. '
                    'Please use format like: namespace/component=1.0.0'
                )

            version_spec = match.group('version') or '*'

            try:
                SimpleSpec(version_spec)
            except ValueError:
                raise click.BadParameter(
                    f'Invalid version specification: "{version_spec}". Please use format like ">=1" or "*".'
                )
    return value


def validate_add_dependency(ctx, param, value):  # noqa: ARG001
    if not value:
        raise click.BadParameter('Name of the dependency can not be an empty string')

    if 'git' not in ctx.params:
        match = re.match(WEB_DEPENDENCY_REGEX, value)
        if match:
            _, spec = match.groups()
        else:
            raise click.BadParameter(
                f'Invalid dependency: "{value}". Please use format "namespace/name".'
            )

        if not spec:
            spec = '*'

        try:
            SimpleSpec(spec)
        except ValueError:
            raise click.BadParameter(
                f'Invalid dependency version requirement: {spec}. '
                'Please use format like ">=1" or "*".'
            )

    return value


# Function to combine multiple callback, order sensetive - each callback will be executed in the order in which it was passed
# If passed callback terminate command execution, it will terminate execution of loop as well
def combined_callback(*callbacks):
    def wrapper(ctx, param, value):
        for callback in callbacks:
            value = callback(ctx, param, value)
        return value

    return wrapper
