# SPDX-FileCopyrightText: 2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os
import typing as t
from collections import deque
from pathlib import Path

from idf_component_manager.dependencies import (
    DownloadedComponent,
    dependency_pre_download_check,
    dependency_validate,
)
from idf_component_tools.build_system_tools import get_idf_path
from idf_component_tools.config import root_managed_components_dir
from idf_component_tools.errors import FetchingError
from idf_component_tools.manager import ManifestManager
from idf_component_tools.manifest import ComponentRequirement, Manifest, SolvedComponent
from idf_component_tools.messages import notice
from idf_component_tools.root_managed_components import (
    RootManagedComponentRecord,
    RootManagedComponentsState,
    RootManagedComponentsStateManager,
    clean_root_managed_components,
    managed_component_path,
    prune_root_managed_components,
    root_managed_components_state_path,
    validate_root_manifest,
)
from idf_component_tools.sources.fetcher import ComponentFetcher
from idf_component_tools.utils import canonical_component_name


def _possible_specs(requirement: ComponentRequirement) -> t.List[str]:
    """
    Return unique version specs declared by a requirement.

    If the requirement has no matches/rules, return its base version, or "*" if unset.
    If it has matches/rules, return the version from each conditional entry.
    When a conditional entry has no version, use the base version instead.
    """
    default = requirement.version or '*'
    optional_dependencies = [*(requirement.matches or []), *(requirement.rules or [])]

    if not optional_dependencies:
        return [default]

    return list({
        optional_dependency.version or default for optional_dependency in optional_dependencies
    })


def _best_versions_per_target(versions: t.List[t.Any]) -> t.List[t.Any]:
    targets = sorted({target for version in versions for target in version.targets})
    selected = []

    if any(not version.targets for version in versions):
        selected.append(max(version for version in versions if not version.targets))

    for target in targets:
        selected.append(
            max(version for version in versions if not version.targets or target in version.targets)
        )

    res = []
    seen = set()
    for version in selected:
        key = (str(version.version), version.component_hash)
        if key in seen:
            continue
        seen.add(key)
        res.append(version)

    return res


def _download_requirement_versions(
    requirement: ComponentRequirement,
    dest_dir: str,
    seen: t.Set[t.Tuple[str, str]],
) -> t.List[DownloadedComponent]:
    if requirement.meta:
        return []

    downloaded = []
    for spec in _possible_specs(requirement):
        component_versions = requirement.source.versions(
            name=requirement.name,
            spec=spec,
            target=None,
        )
        if not component_versions or not component_versions.versions:
            raise FetchingError(f'Cannot find root managed component {requirement.name} ({spec})')

        for version in _best_versions_per_target(component_versions.versions):
            key = (canonical_component_name(requirement.name), str(version.version))
            if key in seen:
                continue
            seen.add(key)

            component = SolvedComponent.fromdict({
                'name': requirement.name,
                'source': requirement.source,
                'version': version.version,
                'dependencies': version.dependencies,
                'component_hash': version.component_hash,
                'targets': version.targets or None,
            })

            component_path = managed_component_path(component, dest_dir)
            download_path = dependency_pre_download_check(component, dest_dir)
            if download_path is None:
                fetcher = ComponentFetcher(component, component_path)
                download_path = fetcher.download()
                dependency_validate(component, download_path)

            if download_path is not None:
                downloaded.append(
                    DownloadedComponent(
                        download_path,
                        component.targets,
                        str(component.version),
                        component_name=component.name,
                    )
                )

    return downloaded


def _remove_untracked_components(
    downloaded_components: t.Set[DownloadedComponent],
    dest_dir: str,
) -> None:
    keep_paths = {Path(component.abs_path).resolve() for component in downloaded_components}
    prune_root_managed_components(dest_dir, keep_paths)


def _download_root_components(manifest: Manifest, dest_dir: str) -> t.Set[DownloadedComponent]:
    """Breadth-first download of every root requirement and its transitive alternatives.

    Seeds the queue with the root manifest's requirements, then enqueues the
    requirements of each newly downloaded component. ``seen`` dedupes by
    (name, version) so every artifact is resolved and downloaded exactly once.
    """
    downloaded: t.Set[DownloadedComponent] = set()
    seen: t.Set[t.Tuple[str, str]] = set()
    queue: t.Deque[ComponentRequirement] = deque(manifest.raw_requirements)

    while queue:
        requirement = queue.popleft()
        for component in _download_requirement_versions(requirement, dest_dir, seen):
            downloaded.add(component)
            component_manifest = ManifestManager(
                component.abs_path, component.component_name or component.name
            ).load()
            queue.extend(component_manifest.raw_requirements)

    return downloaded


def _state_record_from_downloaded(component: DownloadedComponent) -> RootManagedComponentRecord:
    # Record only inventory facts (name/version/path/targets). The installer is
    # authoritative for the downloaded inventory: it resolves each declared spec
    # to a target-covering version set, so configure-time selection does not need
    # any persisted version constraints.
    return RootManagedComponentRecord(
        name=canonical_component_name(component.component_name or component.name),
        version=str(component.version),
        path=component.abs_path,
        targets=tuple(component.targets or ()),
    )


def install_root_components() -> None:
    """
    Download and extract all root managed components from idf_extra_components.yml.

    This function is designed to be called by EIM during
    ESP-IDF installation. It downloads all components needed by the root managed
    component graph and records an install-state file used during project builds.

    Requires IDF_PATH environment variable to be set. Optionally uses IDF_TOOLS_PATH
    (defaults to ~/.espressif).
    """
    idf_path = get_idf_path()
    manifest_filepath = os.path.join(idf_path, 'tools', 'idf_extra_components.yml')
    if not os.path.isfile(manifest_filepath):
        notice('No idf_extra_components.yml found, removing root managed components')
        clean_root_managed_components(root_managed_components_dir())
        return

    manifest = ManifestManager(manifest_filepath, 'root').load()
    validate_root_manifest(manifest)
    if not manifest.dependencies:
        notice('No dependencies in idf_extra_components.yml, removing root managed components')
        clean_root_managed_components(root_managed_components_dir())
        return

    notice(f'Installing root managed components from {manifest_filepath}')

    dest_dir = root_managed_components_dir()
    dest_dir.mkdir(parents=True, exist_ok=True)

    downloaded_components = _download_root_components(manifest, str(dest_dir))
    # Delete stale dirs before writing the new lock. The ordering is deliberately
    # non-transactional: the installer is idempotent, so a crash in between leaves
    # a stale lock that the next run rewrites.
    _remove_untracked_components(downloaded_components, str(dest_dir))
    state = RootManagedComponentsState.from_records(
        manifest.manifest_hash,
        (_state_record_from_downloaded(component) for component in downloaded_components),
    )
    RootManagedComponentsStateManager(root_managed_components_state_path(dest_dir)).dump(state)

    notice('Root managed components installation complete')
