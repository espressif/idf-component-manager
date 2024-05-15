# SPDX-FileCopyrightText: 2023-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import errno
import json
import typing as t
from collections import namedtuple
from pathlib import Path

from tqdm import tqdm

from idf_component_manager.core_utils import parse_component
from idf_component_manager.utils import print_info
from idf_component_tools.build_system_tools import is_component
from idf_component_tools.constants import MANIFEST_FILENAME
from idf_component_tools.errors import SyncError
from idf_component_tools.manager import ManifestManager
from idf_component_tools.manifest import ComponentRequirement
from idf_component_tools.messages import warn
from idf_component_tools.registry.client_errors import ComponentNotFound, VersionNotFound
from idf_component_tools.registry.multi_storage_client import MultiStorageClient
from idf_component_tools.registry.request_processor import join_url
from idf_component_tools.sources.web_service import download_archive

ComponentVersion = namedtuple('ComponentVersion', ['version', 'file_path', 'storage_url'])


class ComponentStaticVersions:  # Should be mutable for updating metadata
    metadata: t.Dict[str, str] = {}
    versions: t.List[ComponentVersion] = []

    def __init__(self, metadata, versions):
        self.metadata = metadata
        self.versions = versions


def dump_metadata(metadata: t.Dict[str, ComponentStaticVersions], save_path: Path) -> None:
    for component_name, component_info in metadata.items():
        namespace, name = component_name.split('/')
        path = save_path / 'components' / namespace
        try:
            path.mkdir(parents=True)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise e

        with open(str(path / f'{name}.json'), 'w') as f:
            json.dump(component_info.metadata, f)


def download_dependency(version: ComponentVersion, path: Path) -> bool:
    if version.storage_url is None:  # Local component
        return False
    filename = Path(version.file_path)
    url = join_url(version.storage_url, str(filename))

    try:
        path.mkdir(parents=True)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise e

    if not (path / filename).is_file():
        download_archive(url, str(path), save_original_filename=True)
        return True
    return False


def download_components_archives(
    metadata: t.Dict[str, ComponentStaticVersions], save_path: Path
) -> t.Dict[str, int]:
    progress_bar = tqdm(total=sum([len(x.versions) for x in metadata.values()]))
    loading_data: t.Dict[str, int] = {}
    for component_name, component_info in metadata.items():
        for version in component_info.versions:
            progress_bar.set_description(f'Downloading {component_name}({version.version})')
            status = download_dependency(version, Path(save_path))
            progress_bar.update(1)
            if status:
                loading_data[component_name] = loading_data.get(component_name, 0) + 1
    progress_bar.close()

    return loading_data


def update_component_metadata(component_metadata: t.Dict, api_metadata: t.Dict) -> t.Dict:
    for api_version in api_metadata['versions']:
        for i, component_version in enumerate(component_metadata['versions']):
            if component_version['version'] == api_version['version']:
                component_metadata['versions'][i] = api_version  # Update old metadata
                break
        else:
            component_metadata['versions'].append(api_version)

    api_metadata['versions'] = component_metadata['versions']  # Update header
    return api_metadata


def update_static_versions(
    old: t.Dict[str, ComponentStaticVersions], new: t.Dict[str, ComponentStaticVersions]
) -> t.Dict:
    result = old.copy()
    for component_name, component_info in new.items():
        if component_name not in result:
            result[component_name] = component_info
        elif result[component_name].metadata != component_info.metadata:
            result[component_name].metadata = update_component_metadata(
                result[component_name].metadata, component_info.metadata
            )

            for version in component_info.versions:
                for i, loaded_version in enumerate(result[component_name].versions):
                    if version.version == loaded_version.version:
                        break
                else:
                    result[component_name].versions.append(version)

    return result


def get_component_metadata(
    client: MultiStorageClient,
    requirement: ComponentRequirement,
    version_spec: t.Optional[str],
    metadata: t.Dict,
    warnings: t.List[str],
    progress_bar: t.Optional[tqdm] = None,
) -> t.Tuple[t.Dict, t.List[str]]:
    try:
        component_info = client.get_component_info(
            component_name=requirement.name, spec=version_spec
        )
        if not component_info.data['versions']:
            raise VersionNotFound()
    except (VersionNotFound, ComponentNotFound):
        warnings.append(
            'Component "{}" with selected spec "{}" was not found in selected storages. '
            'Skip'.format(requirement.name, version_spec)
        )
        return metadata, warnings

    data = component_info.data
    if requirement.name not in metadata:
        metadata[requirement.name] = ComponentStaticVersions(data, [])
    loaded_versions = metadata[requirement.name].versions

    for version in data['versions']:
        for i, loaded_version in enumerate(loaded_versions):
            if version['version'] == loaded_version.version:
                break
        else:
            loaded_versions.append(
                ComponentVersion(version['version'], version['url'], component_info.storage_url)
            )

            if progress_bar:
                progress_bar.update(1)

            deps = client.version_dependencies(version)
            metadata, warnings = prepare_metadata(client, deps, progress_bar, metadata, warnings)

    metadata[requirement.name].versions = loaded_versions

    return metadata, warnings


def prepare_metadata(
    client: MultiStorageClient,
    dependencies: t.List[ComponentRequirement],
    progress_bar: t.Optional[tqdm] = None,
    metadata: t.Optional[t.Dict] = None,
    warnings: t.Optional[t.List] = None,
) -> t.Tuple[t.Dict, t.List[str]]:
    if metadata is None:
        metadata = {}
    if warnings is None:
        warnings = []

    for requirement in dependencies:
        if requirement.source.type == 'service':
            version_specs = []
            if requirement.optional_requirement and requirement.optional_requirement.matches:
                version_specs = [elem.version for elem in requirement.optional_requirement.matches]

            if not version_specs:
                version_specs = [requirement.version_spec]

            for version_spec in version_specs:
                metadata, warnings = get_component_metadata(
                    client, requirement, version_spec, metadata, warnings, progress_bar
                )

    return metadata, warnings


def load_saved_metadata(path: Path) -> t.Dict[str, ComponentStaticVersions]:
    components_json_path = path / 'components'
    metadata = {}
    for json_filename in components_json_path.rglob('*.json'):
        component_name = f'{json_filename.parent.name}/{json_filename.stem}'
        versions = []
        try:
            with open(str(json_filename)) as f:
                loaded_component_metadata = json.load(f)
            for version in loaded_component_metadata['versions']:
                versions.append(ComponentVersion(version['version'], version['url'], None))
        except (ValueError, KeyError):
            raise SyncError('Metadata file is not valid')

        metadata[component_name] = ComponentStaticVersions(loaded_component_metadata, versions)
    return metadata


def collect_metadata(
    client: MultiStorageClient,
    path: t.Union[str, Path],
    components: t.Optional[t.List[str]] = None,
    recursive: bool = False,
) -> t.Dict[str, ComponentStaticVersions]:
    metadata: t.Dict[str, ComponentStaticVersions] = {}
    path = Path(path)
    warnings: t.List[str] = []
    progress_bar = tqdm(
        total=10000,
        desc='Metadata downloaded from the registry',
        bar_format='{desc}: {n_fmt}',
    )  # We don't show total, so we can set total as any big number
    if components:
        dependencies = []
        for component_info in components:
            component_name, spec = parse_component(component_info, client.default_namespace)
            dependencies.append(
                ComponentRequirement(
                    name=component_name,
                    version=spec,
                )
            )
        metadata, warnings = prepare_metadata(
            client, dependencies, progress_bar, metadata, warnings
        )
    else:
        paths = [path]
        if recursive:
            paths = list(path.glob('**'))
        for path in paths:
            if path.is_dir() and is_component(path) and (path / MANIFEST_FILENAME).exists():
                manifest = ManifestManager(str(path), '').load()
                metadata, warnings = prepare_metadata(
                    client, manifest.requirements, progress_bar, metadata, warnings
                )
    progress_bar.close()

    for warning in warnings:
        warn(warning)

    return metadata


def metadata_has_changes(old: t.Dict, new: t.Dict) -> bool:
    if not all(
        x in old['versions'] for x in new['versions']
    ):  # In old metadata may be more versions than in new
        return True

    old_without_version = {k: v for k, v in old.items() if k != 'versions'}
    new_without_version = {k: v for k, v in new.items() if k != 'versions'}
    if old_without_version != new_without_version:
        return True
    return False


def sync_components(
    client: MultiStorageClient,
    path: t.Union[str, Path],
    save_path: Path,
    components: t.Optional[t.List[str]] = None,
    recursive: bool = False,
) -> None:
    save_path = Path(save_path)
    print_info(f'Collecting metadata files into the folder "{save_path.absolute()}"')

    metadata = load_saved_metadata(Path(save_path))
    print_info(f'{len(metadata)} metadata loaded from "{save_path}" folder')

    new_metadata = collect_metadata(client, path, components, recursive)
    if not len(new_metadata):
        raise SyncError('No components found for those requirements')

    if metadata.keys() == new_metadata.keys():
        for component_name in metadata.keys():
            if metadata_has_changes(
                metadata[component_name].metadata, new_metadata[component_name].metadata
            ):
                break
        else:
            print_info('The new metadata is identical to the loaded one. Nothing to update')
            return

    print_info('Updating metadata')
    metadata = update_static_versions(metadata, new_metadata)
    print_info(f'Collected {len(metadata)} components. Downloading archives')

    loading_data = download_components_archives(metadata, save_path)

    dump_metadata(metadata, save_path)

    total_versions = sum(list(loading_data.values()))
    if total_versions:
        print_info(
            'Successfully downloaded {} versions of {} components to the "{}" folder'.format(
                total_versions, len(list(loading_data.keys())), str(save_path)
            )
        )
    else:
        print_info(
            'Metadata was updated, but components had already been downloaded '
            'to the "{}" folder'.format(save_path)
        )
