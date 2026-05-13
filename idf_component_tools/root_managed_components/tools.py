# SPDX-FileCopyrightText: 2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import errno
import os
import shutil
import typing as t
from pathlib import Path

from idf_component_tools.build_system_tools import build_name
from idf_component_tools.config import root_managed_components_dir
from idf_component_tools.constants import DEFAULT_NAMESPACE, MANIFEST_FILENAME
from idf_component_tools.messages import notice

ROOT_MANAGED_COMPONENTS_STATE_FILENAME = 'root_components.lock'

# Top-level entries that legitimately live next to the namespace directories and
# must not be reported as unexpected files.
_ROOT_METADATA_FILES = frozenset({
    ROOT_MANAGED_COMPONENTS_STATE_FILENAME,
    MANIFEST_FILENAME,
    'dependencies.lock',
})

if t.TYPE_CHECKING:
    from idf_component_tools.manifest import SolvedComponent


def is_root_managed_components_path(path: t.Union[str, Path]) -> bool:
    return Path(path).resolve() == root_managed_components_dir().resolve()


def _namespace_and_name(component_name: str) -> t.Tuple[str, str]:
    if '/' in component_name:
        namespace, name = component_name.split('/', 1)
        return namespace, name

    return DEFAULT_NAMESPACE, component_name


def root_managed_component_path(
    root_path: t.Union[str, Path], component_name: str, component_version: t.Any
) -> Path:
    namespace, name = _namespace_and_name(component_name)
    version = str(component_version)

    # The namespace/name/version directories are the storage index and allow
    # multiple installed versions to coexist on disk. The final leaf keeps the
    # existing managed-component build-name convention, e.g. `espressif/foo` ->
    # `espressif__foo`, because the build system and manifest loading derive the
    # component build name from the component directory basename.
    return Path(root_path) / namespace / name / version / build_name(f'{namespace}/{name}')


def managed_component_path(
    component: 'SolvedComponent', managed_components_path: t.Union[str, Path]
) -> Path:
    if is_root_managed_components_path(managed_components_path):
        return root_managed_component_path(
            managed_components_path, component.name, component.version
        )

    return Path(managed_components_path) / build_name(component.name)


def iter_root_managed_component_dirs(root_path: t.Union[str, Path]) -> t.Iterator[Path]:
    root = Path(root_path)
    if not root.exists():
        return

    for component_dir in root.glob('*/*/*/*'):
        if component_dir.is_dir():
            yield component_dir


def remove_empty_root_managed_dirs(root_path: t.Union[str, Path]) -> None:
    root = Path(root_path)
    if not root.exists():
        return

    # Only remove layout container directories (namespace/name/version). Do not
    # recurse into component payloads with rglob(): a component may legitimately
    # ship empty directories, and those must not be deleted here - although unlikely.
    layout_dirs = [
        *(p for p in root.glob('*/*/*') if p.is_dir()),  # version dirs
        *(p for p in root.glob('*/*') if p.is_dir()),  # component-name dirs
        *(p for p in root.glob('*') if p.is_dir()),  # namespace dirs
    ]
    for directory in sorted(layout_dirs, key=lambda p: len(p.parts), reverse=True):
        try:
            directory.rmdir()
        except OSError as e:
            # Non-empty / racing-removal cases are expected and benign; anything
            # else (e.g. permission errors) should surface.
            if e.errno not in {errno.ENOTEMPTY, errno.EEXIST, errno.ENOENT}:
                raise


def prune_root_managed_components(
    root_path: t.Union[str, Path], keep_paths: t.Set[Path]
) -> t.Set[str]:
    """Delete installed root-managed component directories not in ``keep_paths``.

    Encapsulates all knowledge of the namespace/name/version/build_name layout so
    callers only need to provide the set of resolved component paths to keep.
    Returns the set of unexpected top-level entries (anything that is neither a
    layout namespace directory nor known root metadata) for the caller to warn
    about.
    """
    unused_component_dirs = {
        component_dir
        for component_dir in iter_root_managed_component_dirs(root_path)
        if component_dir.resolve() not in keep_paths
    }
    if unused_component_dirs:
        notice(f'Deleting {len(unused_component_dirs)} unused components')
        for component_dir in sorted(unused_component_dirs):
            notice(f' {component_dir}')
            shutil.rmtree(component_dir)

    remove_empty_root_managed_dirs(root_path)

    root = Path(root_path)
    # Namespaces are the top-level layout directories; list them directly instead
    # of iterating every installed version just to read the first path component.
    namespace_dirs = {item.name for item in root.iterdir() if item.is_dir()}
    return set(os.listdir(root)) - namespace_dirs - _ROOT_METADATA_FILES


def root_managed_components_state_path(
    root_path: t.Optional[t.Union[str, Path]] = None,
) -> Path:
    root = Path(root_path) if root_path is not None else root_managed_components_dir()
    return root / ROOT_MANAGED_COMPONENTS_STATE_FILENAME


def clean_root_managed_components(root_path: t.Optional[t.Union[str, Path]] = None) -> None:
    root = Path(root_path) if root_path is not None else root_managed_components_dir()
    if root.exists():
        shutil.rmtree(root)
