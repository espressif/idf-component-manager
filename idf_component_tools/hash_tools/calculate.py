# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
"""Tools for hashing and hash validation for whole packages"""

import json
import typing as t
from hashlib import sha256
from pathlib import Path

from idf_component_tools.file_tools import filtered_paths
from idf_component_tools.hash_tools.constants import BLOCK_SIZE


def hash_object(obj: t.Any) -> str:
    """Calculate sha256 of passed json-serialisable object"""
    sha = sha256()
    json_string = json.dumps(obj, sort_keys=True, separators=(',', ':'))
    sha.update(json_string.encode())
    return sha.hexdigest()


def hash_file(file_path: t.Union[str, Path]) -> str:
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
    root: t.Union[str, Path],
    include: t.Optional[t.Iterable[str]] = None,
    exclude: t.Optional[t.Iterable[str]] = None,
    exclude_default: bool = True,
) -> str:
    """Calculate sha256 of sha256 of all files and file names."""
    sha = sha256()

    paths = sorted(
        filtered_paths(root, include=include, exclude=exclude, exclude_default=exclude_default),
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
