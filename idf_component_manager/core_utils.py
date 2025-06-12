# SPDX-FileCopyrightText: 2022-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import json
import re
import shutil
import typing as t
from pathlib import Path

from ruamel.yaml import YAML
from tqdm import tqdm

from idf_component_tools import notice
from idf_component_tools.constants import DEFAULT_NAMESPACE, MANIFEST_FILENAME
from idf_component_tools.errors import ComponentModifiedError, FatalError, ModifiedComponent
from idf_component_tools.file_tools import (
    check_unexpected_component_files,
)
from idf_component_tools.manager import ManifestManager, UploadMode
from idf_component_tools.manifest import Manifest
from idf_component_tools.manifest.constants import SLUG_BODY_REGEX
from idf_component_tools.semver import SimpleSpec
from idf_component_tools.semver.base import Version
from idf_component_tools.sources.web_service import WebServiceSource

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


def raise_component_modified_error(
    managed_components_dir: str, components: t.List[ModifiedComponent]
) -> None:
    project_path = Path(managed_components_dir).parent
    component_example_name = components[0].name.replace('/', '__')
    managed_component_dir = Path(managed_components_dir, component_example_name)
    component_dir = project_path / 'components' / component_example_name
    error = (
        'Some components in the "managed_components" directory were modified '
        'on the disk since the last run of the CMake.\n\n'
        '{modified_components}\n\n'
        'Content of this directory is managed automatically.\n'
        'If you want to keep the changes, '
        'you can move the directory with the component to the "components" '
        'folder of your project.\n'
        'I.E. for "{component_example}" run:\n'
        'mv {managed_component_dir} {component_dir}\n'
        'If you want to discard the changes, remove the whole component directory from the "managed_components".'
    ).format(
        modified_components='\n'.join([
            f'{component.name}: {component.msg}' for component in components
        ]),
        component_example=component_example_name,
        managed_component_dir=managed_component_dir,
        component_dir=component_dir,
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
    if not dir_path.is_dir():
        return []

    return [
        entry.name
        for entry in dir_path.iterdir()
        if entry.is_dir() and not entry.name.startswith('.')
    ]


def check_examples_folder(
    examples_manifest: t.List[t.Dict[str, str]],
    working_path: Path,
) -> None:
    example_folders = {'examples': collect_directories(working_path / 'examples')}
    error_paths = []
    for example_info in examples_manifest:
        example_path = example_info['path']

        if not (working_path / example_path).is_dir():
            error_paths.append(str(working_path / example_path))
            continue

        if example_path in example_folders.keys():
            raise FatalError(
                'Some paths in the `examples` block in the manifest are listed multiple times: {}. '
                'Please make paths unique and delete duplicate paths'.format(example_path)
            )

        example_folders[example_path] = [Path(example_path).name]

    if error_paths:
        raise FatalError(
            "Example directory doesn't exist: {}.\n"
            'Please check the path of the custom example folder in `examples` field '
            'in `idf_component.yml` file'.format(', '.join(error_paths))
        )


def try_remove_dependency_from_manifest(manifest_path: Path, dependency: str) -> bool:
    yaml = YAML()
    try:
        manifest = yaml.load(manifest_path.read_text(encoding='utf8'))
    except FileNotFoundError:
        raise FatalError(f'Cannot find manifest file at {manifest_path}')

    if 'dependencies' in manifest and dependency in manifest['dependencies']:
        manifest['dependencies'].pop(dependency)
        with open(manifest_path, 'w', encoding='utf8') as manifest_file:
            yaml.dump(manifest, manifest_file)
        return True
    return False


def try_remove_dependency_with_fallback(all_components_info, dependency_name):
    def remove_dependency_and_collect_paths(
        all_component_info: t.Dict, dependency_name: str
    ) -> t.List[Path]:
        removed_from_paths = []

        for component in all_component_info:
            if not component.get('dir'):
                raise FatalError(
                    'Project description file is missing a required "dir" key'
                    'This may indicate an unsupported format version.'
                )

            manifest_path = Path(component.get('dir')) / MANIFEST_FILENAME

            if component.get('source') != 'project_components' or not manifest_path.exists():
                continue

            if try_remove_dependency_from_manifest(manifest_path, dependency_name):
                removed_from_paths.append(manifest_path)

        return removed_from_paths

    # Try to remove dependency (e.g. with included namespace, git, local)
    removed_from_paths = remove_dependency_and_collect_paths(all_components_info, dependency_name)

    # If not found, fallback by prefixing the dependency with espressif namespace
    if not removed_from_paths:
        # Normalize the name (e.g. if no namespace -> "espressif/<component_name>")
        dependency_name = WebServiceSource().normalized_name(dependency_name)
        removed_from_paths = remove_dependency_and_collect_paths(
            all_components_info, dependency_name
        )

    return removed_from_paths


def validate_project_description_version(project_description: dict):
    version = project_description.get('version', 'unknown')

    if version == 'unknown':
        raise FatalError('Project description file is missing version information')

    v = Version.coerce(version)
    supported = (Version.coerce('1.3') <= v < Version.coerce('2.0')) or (
        v >= Version.coerce('2.0') and 'all_component_info' in project_description
    )

    if not supported:
        raise FatalError(f'project_description.json format version {version} is not supported.')


def load_project_description_file(build_path):
    try:
        return json.loads((build_path / 'project_description.json').read_text())
    except FileNotFoundError:
        raise FatalError(
            f'Cannot find project description file at {build_path / "project_description.json"}'
        )
    except json.JSONDecodeError as e:
        raise FatalError(f'Invalid JSON in project description file: {e}')
    except Exception as e:
        raise FatalError(f'Error reading project description file: {e}')
