# SPDX-FileCopyrightText: 2023-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os
import re
import typing as t
from pathlib import Path

from idf_component_tools.constants import MANIFEST_FILENAME
from idf_component_tools.environment import getenv_bool
from idf_component_tools.manager import ManifestManager

from .constants import HASH_FILENAME, SHA256_RE
from .errors import HashDoesNotExistError, HashNotEqualError, HashNotSHA256Error
from .validator import validate_dir


def validate_managed_component_by_manifest(
    root: t.Union[str, Path],
    component_hash: str,
) -> bool:
    # TODO Te dependency is weird
    #   move to source?

    """Validate component in managed directory"""
    manifest_file_path = os.path.join(root, MANIFEST_FILENAME)

    manifest_manager = ManifestManager(manifest_file_path, 'cmp')
    manifest = manifest_manager.load()
    exclude_set = set(manifest.exclude_set)
    exclude_set.add('**/.component_hash')

    return validate_dir(
        root,
        component_hash,
        include=manifest.include_set,
        exclude=exclude_set,
        exclude_default=False,
    )


def validate_managed_component_hash(root: str) -> None:
    """Validate managed components directory, raise exception if validation fails"""
    if getenv_bool('IDF_COMPONENT_OVERWRITE_MANAGED_COMPONENTS'):
        return

    hash_file_path = os.path.join(root, HASH_FILENAME)

    if not os.path.isdir(root) or not os.path.exists(hash_file_path):
        raise HashDoesNotExistError()

    with open(hash_file_path, encoding='utf-8') as f:
        hash_from_file = f.read().strip()

    if not re.match(SHA256_RE, hash_from_file):
        raise HashNotSHA256Error()

    if not validate_managed_component_by_manifest(root, hash_from_file):
        raise HashNotEqualError()
