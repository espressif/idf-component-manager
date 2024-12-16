# SPDX-FileCopyrightText: 2023-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import errno
import json
import typing as t
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from idf_component_manager.core_utils import parse_component_name_spec
from idf_component_manager.utils import VersionSolverResolution
from idf_component_tools import get_logger
from idf_component_tools.build_system_tools import is_component
from idf_component_tools.constants import MANIFEST_FILENAME
from idf_component_tools.errors import SyncError
from idf_component_tools.hash_tools.constants import CHECKSUMS_FILENAME
from idf_component_tools.manager import ManifestManager
from idf_component_tools.manifest import ComponentRequirement
from idf_component_tools.messages import error, notice, warn
from idf_component_tools.registry.client_errors import ComponentNotFound, VersionNotFound
from idf_component_tools.registry.multi_storage_client import MultiStorageClient
from idf_component_tools.registry.request_processor import join_url
from idf_component_tools.registry.storage_client import StorageClient
from idf_component_tools.semver import Version
from idf_component_tools.sources.web_service import download_archive, download_file

LOGGER = get_logger()


@dataclass
class DownloadComponentVersion:
    version: Version
    storage_url: t.Optional[str] = None

    def __hash__(self) -> int:
        return hash(self.version)


class PartialMirror:
    """This class holds all the required versions of a component"""

    def __init__(self):
        self.data: t.Dict[str, t.Set[DownloadComponentVersion]] = defaultdict(set)

    def update(self, component_name: str, version: DownloadComponentVersion) -> None:
        self.data[component_name].add(version)

    def merge(self, other: 'PartialMirror') -> None:
        for component_name, comp_versions in other.data.items():
            self.data[component_name].update(comp_versions)

    def diff(self, other: 'PartialMirror') -> 'PartialMirror':
        """self.versions - other.versions"""
        diff = PartialMirror()
        for component_name, comp_versions in self.data.items():
            for version in comp_versions:
                if version.version not in [
                    v.version for v in other.data.get(component_name, set())
                ]:
                    diff.update(component_name, version)
        return diff


def download_versions_from_storage(
    storage_url: str,
    component_name: str,
    versions: t.Set[DownloadComponentVersion],
    output_dir: Path,
    progress_bar: t.Optional[tqdm] = None,
) -> None:
    component_json = StorageClient(storage_url).get_component_json(
        component_name=component_name
    )  # full component json
    component_json_version_urls = {
        Version(ver['version']): {
            'url': ver['url'],
            'checksums_url': ver['checksums'],
        }
        for ver in component_json['versions']
    }

    for version in versions:
        if version.version not in component_json_version_urls:
            error(f'Version {version.version} of component {component_name} not found in storage')
            continue

        if progress_bar is not None:
            progress_bar.set_description(f'Downloading {component_name}({version.version})')
            progress_bar.update(1)

        download_url = join_url(storage_url, component_json_version_urls[version.version]['url'])
        checksums_url = join_url(
            storage_url, component_json_version_urls[version.version]['checksums_url']
        )
        ver_output = (output_dir / component_json_version_urls[version.version]['url']).parent
        try:
            ver_output.mkdir(parents=True)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise e

        download_archive(download_url, str(ver_output), save_original_filename=True)
        download_file(checksums_url, str(ver_output))

    # trim component json
    trimmed_component_json = deepcopy(component_json)
    trimmed_component_json['versions'] = [
        ver
        for ver in component_json['versions']
        if Version(ver['version']) in {v.version for v in versions}
    ]

    comp_json_filepath = output_dir / 'components' / f'{component_name}.json'
    if comp_json_filepath.exists():
        # merging local cmp.json
        with open(str(comp_json_filepath), encoding='utf-8') as fr:
            old_json_dict = json.load(fr)
            old_json_dict['versions'].extend(trimmed_component_json['versions'])

        with open(str(comp_json_filepath), 'w', encoding='utf-8') as fw:
            json.dump(old_json_dict, fw)
    else:
        comp_json_filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(str(comp_json_filepath), 'w', encoding='utf-8') as fw:
            json.dump(trimmed_component_json, fw)


def download_components_archives(
    new_partial_mirror: PartialMirror, old_partial_mirror: PartialMirror, output_dir: Path
) -> int:
    diff = new_partial_mirror.diff(old_partial_mirror)
    total_downloads = sum(len(versions) for versions in diff.data.values())
    progress_bar = tqdm(total=total_downloads)

    for component_name, component_versions in diff.data.items():
        # group by storage_url
        component_versions_by_storage: t.Dict[str, t.Set[DownloadComponentVersion]] = defaultdict(
            set
        )
        for v in component_versions:
            if not v.storage_url:
                warn(
                    f'No storage url for component {component_name} version {v.version}. Skipping download...'
                )
                continue
            component_versions_by_storage[v.storage_url].add(v)

        for storage_url, versions in component_versions_by_storage.items():
            with logging_redirect_tqdm(loggers=[LOGGER]):
                download_versions_from_storage(
                    storage_url,
                    component_name,
                    versions,
                    output_dir,
                    progress_bar=progress_bar,
                )

    progress_bar.close()
    return total_downloads


def prepare_component_versions(
    client: MultiStorageClient,
    requirements: t.List[ComponentRequirement],
    *,
    # not required
    progress_bar: t.Optional[tqdm] = None,
    resolution: VersionSolverResolution = VersionSolverResolution.ALL,
    # caches
    solved_requirements_cache: t.Set[ComponentRequirement] = None,  # type: ignore
    recorded_versions_cache: t.Dict[str, t.Set[Version]] = None,  # type: ignore
) -> PartialMirror:
    if solved_requirements_cache is None:
        solved_requirements_cache = set()
    if recorded_versions_cache is None:
        recorded_versions_cache = defaultdict(set)

    def _prepare_component_versions(
        _reqs: t.List[ComponentRequirement],
    ) -> PartialMirror:
        _partial_mirror = PartialMirror()
        for req in _reqs:
            if req.source.type != 'service':
                continue

            if req in solved_requirements_cache:
                continue

            solved_requirements_cache.add(req)

            try:
                component_with_versions, storage_url = client.get_component_versions(
                    req, resolution=resolution
                )
                if not component_with_versions.versions:
                    raise VersionNotFound()
            except (VersionNotFound, ComponentNotFound):
                warn(
                    f'Component "{req.name}" with selected version "{req.version}" '
                    f'was not found in selected storages. Skipping...'
                )
                return _partial_mirror

            for version in component_with_versions.versions:
                _partial_mirror.update(
                    req.name,
                    DownloadComponentVersion(
                        version=Version(version.version),
                        storage_url=storage_url,
                    ),
                )

                if progress_bar is not None:
                    if version.version.semver not in recorded_versions_cache.get(req.name, set()):
                        recorded_versions_cache[req.name].add(version.version.semver)
                        progress_bar.update(1)

                _partial_mirror.merge(
                    _prepare_component_versions(
                        version.dependencies,
                    )
                )

        return _partial_mirror

    return _prepare_component_versions(requirements)


def load_local_mirror(path: Path) -> PartialMirror:
    res = PartialMirror()

    for json_filename in (path / 'components').rglob('*.json'):
        # Skip files with checksums
        if json_filename.name == CHECKSUMS_FILENAME:
            continue

        component_name = f'{json_filename.parent.name}/{json_filename.stem}'

        try:
            with open(str(json_filename), encoding='utf-8') as f:
                response = json.load(f)
        except (ValueError, KeyError):
            error(f'Ignoring invalid metadata file: {json_filename}')
            continue

        for version in response['versions']:
            res.update(
                component_name, DownloadComponentVersion(version=Version(version['version']))
            )

    return res


def collect_component_versions(
    client: MultiStorageClient,
    path: t.Union[str, Path],
    component_specs: t.Optional[t.List[str]] = None,
    recursive: bool = False,
    resolution: VersionSolverResolution = VersionSolverResolution.ALL,
) -> PartialMirror:
    path = Path(path)
    progress_bar = tqdm(
        desc='Collecting required components',
        bar_format='{desc}: {n_fmt}',
    )
    solved_requirements_cache: t.Set[ComponentRequirement] = set()
    recorded_versions_cache: t.Dict[str, t.Set[Version]] = defaultdict(set)

    if component_specs:
        dependencies = []
        for component_requirements in component_specs:
            namespace, component, spec = parse_component_name_spec(
                component_requirements, client.default_namespace
            )
            dependencies.append(
                # only service source supported
                ComponentRequirement(
                    name=f'{namespace}/{component}',
                    version=spec,
                )
            )
            with logging_redirect_tqdm(loggers=[LOGGER]):
                res = prepare_component_versions(
                    client,
                    dependencies,
                    progress_bar=progress_bar,
                    resolution=resolution,
                    solved_requirements_cache=solved_requirements_cache,
                    recorded_versions_cache=recorded_versions_cache,
                )
    else:
        paths = [path]
        if recursive:
            paths = list(path.glob('**'))

        res = PartialMirror()
        for path in paths:
            if path.is_dir() and is_component(path) and (path / MANIFEST_FILENAME).exists():
                manifest = ManifestManager(path, '').load()
                with logging_redirect_tqdm(loggers=[LOGGER]):
                    res.merge(
                        prepare_component_versions(
                            client,
                            manifest.raw_requirements,
                            progress_bar=progress_bar,
                            resolution=resolution,
                            solved_requirements_cache=solved_requirements_cache,
                            recorded_versions_cache=recorded_versions_cache,
                        )
                    )

    progress_bar.close()

    return res


def sync_components(
    client: MultiStorageClient,
    work_dir: t.Union[str, Path],
    output_dir: Path,
    components: t.Optional[t.List[str]] = None,
    recursive: bool = False,
    resolution: VersionSolverResolution = VersionSolverResolution.ALL,
) -> None:
    output_dir = Path(output_dir)
    notice(f'Collecting local storage from folder "{output_dir.absolute()}"')
    local_component_versions = load_local_mirror(Path(output_dir))
    notice(f'{len(local_component_versions.data)} components loaded from "{output_dir}" folder')

    new_component_versions = collect_component_versions(
        client,
        work_dir,
        component_specs=components,
        recursive=recursive,
        resolution=resolution,
    )
    if not len(new_component_versions.data):
        raise SyncError('No component need to be downloaded with the specified requirements')

    # download & copy cmp.jsons
    newly_downloads = download_components_archives(
        new_component_versions, local_component_versions, output_dir
    )
    notice(f'{newly_downloads} new files downloaded')
