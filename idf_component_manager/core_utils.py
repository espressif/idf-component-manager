# SPDX-FileCopyrightText: 2022 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import re
from pathlib import Path

from tqdm import tqdm

from idf_component_tools.constants import DEFAULT_NAMESPACE
from idf_component_tools.errors import ComponentModifiedError, FatalError
from idf_component_tools.hash_tools import HASH_FILENAME
from idf_component_tools.manifest import Manifest
from idf_component_tools.semver import SimpleSpec

CREATE_PROJECT_FROM_EXAMPLE_NAME_REGEX = r'^((?P<namespace>\w+)\/)?' \
                                         r'(?P<component>\w+)' \
                                         r'(?P<version>[<=>!^~\*].+)?:' \
                                         r'(?P<example>[\w\/]+)$'


class ProgressBar(tqdm):
    """Wrapper for tqdm for updating progress bar status"""
    def update_to(self, count):  # type: (int) -> bool | None
        return self.update(count - self.n)


def dist_name(manifest):  # type: (Manifest) -> str
    if manifest.version is None:
        raise ValueError('Version is required in this manifest')

    return '{}_{}'.format(manifest.name, manifest.version)


def archive_filename(manifest):  # type: (Manifest) -> str
    return '{}.tgz'.format(dist_name(manifest))


def raise_component_modified_error(managed_components_dir, components):  # type: (str, list[str]) -> None
    project_path = Path(managed_components_dir).parent
    component_example_name = components[0].replace('/', '__')
    managed_component_dir = Path(managed_components_dir, component_example_name)
    component_dir = project_path / 'components' / component_example_name
    hash_path = managed_component_dir / HASH_FILENAME
    error = """
        Some components ({component_names}) in the "managed_components" directory were modified \
        on the disk since the last run of the CMake. Content of this directory is managed automatically.

        If you want to keep the changes, you can move the directory with the component to the "components" \
        directory of your project.

        I.E. for "{component_example}" run:
        mv {managed_component_dir} {component_dir}

        Or, if you want to discard the changes remove the "{hash_filename}" file from the component\'s directory.

        I.E. for "{component_example}" run:
        rm {hash_path}
        """.format(
        component_names=', '.join(components),
        component_example=component_example_name,
        managed_component_dir=managed_component_dir,
        component_dir=component_dir,
        hash_path=hash_path,
        hash_filename=HASH_FILENAME)
    raise ComponentModifiedError(error)


def parse_example(example):  # type: (str) -> tuple[str, str, str]
    match = re.match(CREATE_PROJECT_FROM_EXAMPLE_NAME_REGEX, example)
    if not match:
        raise FatalError(
            'Cannot parse EXAMPLE argument. Please use format like: namespace/component=1.0.0:example_name')

    namespace = match.group('namespace') or DEFAULT_NAMESPACE
    component = match.group('component')
    version_spec = match.group('version') or '*'
    example_name = match.group('example')

    try:
        SimpleSpec(version_spec)
    except ValueError:
        raise FatalError(
            'Invalid version specification: "{}". Please use format like ">=1" or "*".'.format(version_spec))

    return '{}/{}'.format(namespace, component), version_spec, example_name
