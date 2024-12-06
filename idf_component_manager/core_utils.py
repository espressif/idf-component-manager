# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os
import re
import shutil
import typing as t
from pathlib import Path

from tqdm import tqdm

from idf_component_tools import notice
from idf_component_tools.constants import DEFAULT_NAMESPACE, MANIFEST_FILENAME
from idf_component_tools.errors import ComponentModifiedError, FatalError
from idf_component_tools.file_tools import (
    check_unexpected_component_files,
    copy_directories,
    filtered_paths,
)
from idf_component_tools.hash_tools.constants import HASH_FILENAME
from idf_component_tools.manager import ManifestManager, UploadMode
from idf_component_tools.manifest import Manifest
from idf_component_tools.manifest.constants import SLUG_BODY_REGEX
from idf_component_tools.semver import SimpleSpec

CREATE_PROJECT_FROM_EXAMPLE_NAME_REGEX = (
    r'^((?P<namespace>{slug})\/)?'
    r'(?P<component>{slug})'
    r'(?P<version>[<=>!^~\*].+)?:'
    r'(?P<example>[/a-zA-Z\d_\-\.\+]+)$'
).format(slug=SLUG_BODY_REGEX)

COMPONENT_FULL_NAME_WITH_SPEC_REGEX = (
    r'^((?P<namespace>{slug})\/)?(?P<component>{slug})(?P<version>[<=>!^~\*].+)?'
).format(slug=SLUG_BODY_REGEX)


class ProgressBar(tqdm):
    """Wrapper for tqdm for updating progress bar status"""

    def update_to(self, count: t.Union[int, float]) -> t.Optional[bool]:
        return self.update(count - self.n)


def dist_name(name: str, version: str) -> str:
    return f'{name}_{version}'


def archive_filename(name: str, version: str) -> str:
    return f'{dist_name(name, version)}.tgz'


def _create_manifest_if_missing(manifest_dir: Path) -> bool:
    manifest_filepath = Path(manifest_dir) / MANIFEST_FILENAME
    if manifest_filepath.exists():
        return False
    example_path = Path(__file__).resolve().parent / 'templates' / 'idf_component_template.yml'
    manifest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(example_path, manifest_filepath)
    notice(f'Created "{manifest_filepath}"')
    return True


def get_validated_manifest(manifest_manager: ManifestManager, path: str) -> Manifest:
    """
    Get the validated manifest for the given path.

    :param manifest_manager: The ManifestManager object used to load the manifest.
    :param path: The path to the manifest file.
    :return: The validated Manifest object.

    :raises ManifestError: If the manifest file is invalid.
    """
    manifest = manifest_manager.load()
    validate_examples_manifest(path)
    check_unexpected_component_files(path)
    return manifest


def validate_examples_manifest(path: str) -> None:
    """
    Validates the manifest files in the examples directory.

    :param path: The path to the component directory.
    :type path: str

    :raises ManifestError: If the manifest file is invalid.
    """

    examples_path = Path(path) / 'examples'

    if not examples_path.exists():
        return None

    # Find all manifest files in examples directory
    for manifest_path in examples_path.rglob(MANIFEST_FILENAME):
        # Check if the manifest file is valid
        ManifestManager(
            manifest_path, manifest_path.parent.parent.name, upload_mode=UploadMode.example
        ).load()


def raise_component_modified_error(managed_components_dir: str, components: t.List[str]) -> None:
    project_path = Path(managed_components_dir).parent
    component_example_name = components[0].replace('/', '__')
    managed_component_dir = Path(managed_components_dir, component_example_name)
    component_dir = project_path / 'components' / component_example_name
    hash_path = managed_component_dir / HASH_FILENAME
    error = (
        'Some components ({component_names}) in the "managed_components" directory were modified '
        'on the disk since the last run of the CMake. '
        'Content of this directory is managed automatically.\n'
        'If you want to keep the changes, '
        'you can move the directory with the component to the "components"'
        'directory of your project.\n'
        'I.E. for "{component_example}" run:\n'
        'mv {managed_component_dir} {component_dir}\n'
        'Or, if you want to discard the changes remove the "{hash_filename}" file '
        "from the component's directory.\n"
        'I.E. for "{component_example}" run:\n'
        'rm {hash_path}'
    ).format(
        component_names=', '.join(components),
        component_example=component_example_name,
        managed_component_dir=managed_component_dir,
        component_dir=component_dir,
        hash_path=hash_path,
        hash_filename=HASH_FILENAME,
    )
    raise ComponentModifiedError(error)


def parse_example(example: str, namespace: str) -> t.Tuple[str, str, str]:
    match = re.match(CREATE_PROJECT_FROM_EXAMPLE_NAME_REGEX, example)
    if not match:
        raise FatalError(
            'Cannot parse EXAMPLE argument. '
            'Please use format like: namespace/component=1.0.0:example_name'
        )

    namespace = match.group('namespace') or namespace
    component = match.group('component')
    version_spec = match.group('version') or '*'
    example_name = match.group('example')

    try:
        SimpleSpec(version_spec)
    except ValueError:
        raise FatalError(
            f'Invalid version specification: "{version_spec}". Please use format like ">=1" or "*".'
        )

    return f'{namespace}/{component}', version_spec, example_name


def parse_component_name_spec(
    component_name: str,
    default_namespace=DEFAULT_NAMESPACE,
    default_spec: str = '*',
) -> t.Tuple[str, str, str]:
    match = re.match(COMPONENT_FULL_NAME_WITH_SPEC_REGEX, component_name)
    if not match:
        raise FatalError(
            'Cannot parse COMPONENT argument. Please use format like: namespace/component=1.0.0'
        )

    namespace = match.group('namespace') or default_namespace or DEFAULT_NAMESPACE
    name = match.group('component')
    spec = match.group('version') or default_spec

    try:
        SimpleSpec(spec)
    except ValueError:
        raise FatalError(
            f'Invalid version specification: "{spec}". Please use format like ">=1" or "*".'
        )

    return namespace, name, spec


def collect_directories(dir_path: Path) -> t.List[str]:
    directories: t.List[str] = []
    if not dir_path.is_dir():
        return directories

    for directory in os.listdir(str(dir_path)):
        if directory.startswith('.') or not (dir_path / directory).is_dir():
            continue

        directories.append(directory)

    return directories


def detect_duplicate_examples(example_folders, example_path, example_name):
    for key, value in example_folders.items():
        if example_name in value:
            return key, example_path, example_name
    return


def copy_examples_folders(
    examples_manifest: t.List[t.Dict[str, str]],
    working_path: Path,
    dist_dir: Path,
    use_gitignore: bool = False,
    include: t.Optional[t.Set[str]] = None,
    exclude: t.Optional[t.Set[str]] = None,
) -> None:
    examples_path = working_path / 'examples'
    example_folders = {'examples': collect_directories(examples_path)}
    error_paths = []
    duplicate_paths = []
    for example_info in examples_manifest:
        example_path = example_info['path']
        example_name = Path(example_path).name
        full_example_path = working_path / example_path

        if not full_example_path.is_dir():
            error_paths.append(str(full_example_path))
            continue

        if example_path in example_folders.keys():
            raise FatalError(
                'Some paths in the `examples` block in the manifest are listed multiple times: {}. '
                'Please make paths unique and delete duplicate paths'.format(example_path)
            )

        duplicates = detect_duplicate_examples(example_folders, example_path, example_name)
        if duplicates:
            duplicate_paths.append(duplicates)
            continue

        example_folders[example_path] = [example_name]

        paths = filtered_paths(
            full_example_path, use_gitignore=use_gitignore, include=include, exclude=exclude
        )
        copy_directories(str(full_example_path), str(dist_dir / 'examples' / example_name), paths)

    if error_paths:
        raise FatalError(
            "Example directory doesn't exist: {}.\n"
            'Please check the path of the custom example folder in `examples` field '
            'in `idf_component.yml` file'.format(', '.join(error_paths))
        )

    if duplicate_paths:
        error_messages = []
        for first_path, second_path, example_name in duplicate_paths:
            error_messages.append(
                f'Examples from "{first_path}" and "{second_path}" '
                f'have the same name: {example_name}.'
            )
        error_messages.append('Please rename one of them, or delete if there are the same')

        raise FatalError('\n'.join(error_messages))
