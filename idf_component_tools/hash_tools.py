# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
"""Tools for hashing and hash validation for whole packages"""
import json
import os
import re
from hashlib import sha256
from io import open
from pathlib import Path

from idf_component_tools.environment import getenv_bool
from idf_component_tools.file_tools import filtered_paths

try:
    from typing import Any, Iterable, Text
except ImportError:
    pass

BLOCK_SIZE = 65536
HASH_FILENAME = '.component_hash'
SHA256_RE = r'^[A-Fa-f0-9]{64}$'


class ValidatingHashError(Exception):
    pass


class HashNotEqualError(ValidatingHashError):
    pass


class HashNotSHA256Error(ValidatingHashError):
    pass


class HashDoesNotExistError(ValidatingHashError):
    pass


def hash_object(obj):  # type: (Any) -> str
    """Calculate sha256 of passed json-serialisable object"""
    sha = sha256()
    json_string = json.dumps(obj, sort_keys=True, separators=(',', ':'))
    sha.update(json_string.encode())
    return sha.hexdigest()


def hash_file(file_path):  # type: (Text | Path) -> str
    """Calculate sha256 of file"""
    sha = sha256()

    with open(Path(file_path).as_posix(), 'rb') as f:
        while True:
            block = f.read(BLOCK_SIZE)
            if not block:
                break
            sha.update(block)

    return sha.hexdigest()


def hash_dir(
    root,  # type: Text | Path
    exclude=None,  # type: Iterable[Text] | None
    exclude_default=True,  # type: bool
):  # type: (...) -> str
    """Calculate sha256 of sha256 of all files and file names."""
    sha = sha256()

    paths = sorted(
        filtered_paths(root, exclude=exclude, exclude_default=exclude_default),
        key=lambda path: path.relative_to(root).as_posix(),
    )
    for file_path in paths:
        if file_path.is_dir():
            continue

        # Add file path
        sha.update(file_path.relative_to(root).as_posix().encode('utf-8'))

        # Add content hash
        sha.update(hash_file(file_path).encode('utf-8'))

    return sha.hexdigest()


def validate_dir(
    root,  # type: Text | Path
    dir_hash,  # type: Text
    exclude=None,  # type: Iterable[Text] | None
    exclude_default=True,  # type: bool
):
    # type: (...) -> bool
    """Check if directory hash is the same as provided"""
    current_hash = Path(root).is_dir() and hash_dir(
        root, exclude=exclude, exclude_default=exclude_default
    )
    return current_hash == dir_hash


def validate_filtered_dir(root, component_hash):  # type: (Text | Path, str) -> bool
    """Validate component in managed directory"""
    return validate_dir(root, component_hash, exclude=['**/.component_hash'], exclude_default=False)


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

    if not validate_filtered_dir(root, hash_from_file):
        raise HashNotEqualError()
