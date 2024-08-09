# SPDX-FileCopyrightText: 2023-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os
import re
import typing as t
from pathlib import Path

from idf_component_tools import ComponentManagerSettings
from idf_component_tools.manager import ManifestManager

from .calculate import hash_dir
from .constants import HASH_FILENAME, SHA256_RE
from .errors import HashDoesNotExistError, HashNotEqualError, HashNotSHA256Error


def validate_managed_component_by_hashdir(
    root: t.Union[str, Path],
    expected_component_hash: str,
) -> bool:
    manifest_manager = ManifestManager(root, 'cmp')
    manifest = manifest_manager.load()

    exclude_set = set(manifest.exclude_set)
    exclude_set.add('**/.component_hash')

    return validate_dir(
        root,
        expected_component_hash,
        use_gitignore=manifest.use_gitignore,
        include=manifest.include_set,
        exclude=exclude_set,
        exclude_default=False,
    )


def validate_managed_component_by_hashfile(
    root: t.Union[str, Path],
    expected_component_hash: str,
) -> bool:
    if not os.path.isdir(root):
        return False

    hash_file_path = os.path.join(root, HASH_FILENAME)
    if not os.path.isfile(hash_file_path):
        return False

    with open(hash_file_path, encoding='utf-8') as f:
        hash_from_file = f.read().strip()

    if not re.match(SHA256_RE, hash_from_file):
        raise HashNotSHA256Error()

    return hash_from_file == expected_component_hash


def validate_managed_component_hash(root: str) -> None:
    """Validate managed components directory, raise exception if validation fails"""
    if ComponentManagerSettings().OVERWRITE_MANAGED_COMPONENTS:
        return

    hash_file_path = os.path.join(root, HASH_FILENAME)

    if not os.path.isdir(root) or not os.path.exists(hash_file_path):
        raise HashDoesNotExistError()

    with open(hash_file_path, encoding='utf-8') as f:
        hash_from_file = f.read().strip()

    if not re.match(SHA256_RE, hash_from_file):
        raise HashNotSHA256Error()

    if not validate_managed_component_by_hashdir(root, hash_from_file):
        raise HashNotEqualError()


def validate_dir(
    root: t.Union[str, Path],
    dir_hash: str,
    use_gitignore: bool = False,
    include: t.Optional[t.Iterable[str]] = None,
    exclude: t.Optional[t.Iterable[str]] = None,
    exclude_default: bool = True,
) -> bool:
    """Check if directory hash is the same as provided"""
    current_hash = Path(root).is_dir() and hash_dir(
        root,
        use_gitignore=use_gitignore,
        include=include,
        exclude=exclude,
        exclude_default=exclude_default,
    )
    return current_hash == dir_hash
