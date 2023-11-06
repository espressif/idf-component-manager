# SPDX-FileCopyrightText: 2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os
import re
from io import open
from pathlib import Path

from idf_component_tools.environment import getenv_bool
from idf_component_tools.hash_tools import (
    HASH_FILENAME,
    SHA256_RE,
    HashDoesNotExistError,
    HashNotEqualError,
    HashNotSHA256Error,
    hash_dir,
)

try:
    from typing import Any, Iterable, Text
except ImportError:
    pass


def validate_dir(
    root,  # type: Text | Path
    dir_hash,  # type: Text
    include=None,  # type Iterable[Text] | None
    exclude=None,  # type: Iterable[Text] | None
    exclude_default=True,  # type: bool
):
    # type: (...) -> bool
    """Check if directory hash is the same as provided"""
    current_hash = Path(root).is_dir() and hash_dir(
        root, include=include, exclude=exclude, exclude_default=exclude_default
    )
    return current_hash == dir_hash


def validate_managed_component(
    root,  # type: Text | Path
    component_hash,  # type: str
):  # type: (...) -> bool
    """Validate component in managed directory"""
    from idf_component_tools.manifest import MANIFEST_FILENAME, ManifestManager

    manifest_file_path = os.path.join(root, MANIFEST_FILENAME)

    manifest_manager = ManifestManager(manifest_file_path, 'cmp')
    manifest = manifest_manager.load()
    include = set(manifest.files['include'])
    exclude = set(manifest.files['exclude'])
    exclude.add('**/.component_hash')

    return validate_dir(
        root, component_hash, include=include, exclude=exclude, exclude_default=False
    )


def validate_managed_component_hash(root):  # type: (str) -> None
    '''Validate managed components directory, raise exception if validation fails'''
    if getenv_bool('IDF_COMPONENT_OVERWRITE_MANAGED_COMPONENTS'):
        return

    hash_file_path = os.path.join(root, HASH_FILENAME)

    if not os.path.isdir(root) or not os.path.exists(hash_file_path):
        raise HashDoesNotExistError()

    with open(hash_file_path, mode='r', encoding='utf-8') as f:
        hash_from_file = f.read().strip()

    if not re.match(SHA256_RE, hash_from_file):
        raise HashNotSHA256Error()

    if not validate_managed_component(root, hash_from_file):
        raise HashNotEqualError()
