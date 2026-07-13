# SPDX-FileCopyrightText: 2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
"""Helpers for the ``compote manifest lint`` command."""

import typing as t
from pathlib import Path

from idf_component_tools.constants import MANIFEST_FILENAME
from idf_component_tools.errors import FatalError

# Directories skipped when discovering manifests for linting. ``managed_components``
# contains downloaded dependencies; ``dist`` contains packaging artifacts.
LINT_EXCLUDED_DIRS = frozenset({'managed_components', 'dist'})

# Exit code used when `compote manifest lint` finds invalid manifests. Follows the
# common linter convention: 0 = everything valid, 1 = problems found.
LINT_PROBLEMS_EXIT_CODE = 1


def collect_manifests_for_lint(paths: t.Iterable[t.Union[str, Path]]) -> t.List[Path]:
    """
    Resolve the list of manifest files to validate.

    Directories are searched recursively; explicitly given files are used as-is
    and must be named ``idf_component.yml``. The result is de-duplicated,
    preserving order.
    """
    manifest_paths: t.List[Path] = []
    for raw_path in paths:
        path = Path(raw_path)
        if path.is_dir():
            manifest_paths.extend(discover_manifests_for_lint(path))
        elif path.is_file():
            if path.name != MANIFEST_FILENAME:
                raise FatalError(
                    f'"{path}" is not a manifest file (expected a file named "{MANIFEST_FILENAME}")'
                )
            manifest_paths.append(path)
        else:
            raise FatalError(f'Path does not exist: "{path}"')

    seen: t.Set[Path] = set()
    unique_paths: t.List[Path] = []
    for manifest_path in manifest_paths:
        resolved = manifest_path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique_paths.append(manifest_path)
    return unique_paths


def discover_manifests_for_lint(root: Path) -> t.List[Path]:
    """
    Find manifest files under ``root``, skipping downloaded dependencies,
    packaging artifacts, and hidden directories.
    """
    manifest_paths: t.List[Path] = []
    for manifest_path in sorted(root.rglob(MANIFEST_FILENAME)):
        directories = manifest_path.relative_to(root).parts[:-1]
        if any(
            directory in LINT_EXCLUDED_DIRS or directory.startswith('.')
            for directory in directories
        ):
            continue
        manifest_paths.append(manifest_path)
    return manifest_paths
