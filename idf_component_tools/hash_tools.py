"""Tools for hashing and hash validation for whole packages"""
import json
from hashlib import sha256
from io import open
from pathlib import Path

from .file_tools import DEFAULT_EXCLUDE, filtered_paths

try:
    from typing import Any, Iterable, Optional, Text, Union
except ImportError:
    pass

BLOCK_SIZE = 65536


def hash_object(obj):  # type: (Any) -> str
    """Calculate sha256 of passed json-serialisable object"""
    sha = sha256()
    json_string = json.dumps(obj, sort_keys=True, separators=(',', ':'))
    sha.update(json_string.encode())
    return sha.hexdigest()


def hash_file(file_path):  # type: (Union[Text, Path]) -> str
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
        root,  # type: Union[Text, Path]
        exclude=None  # type: Optional[Iterable[Text]]
):  # type: (...) -> str
    """Calculate sha256 of sha256 of all files and file names."""
    sha = sha256()

    if exclude is None:
        exclude = DEFAULT_EXCLUDE

    paths = sorted(filtered_paths(root, exclude=exclude), key=lambda path: path.relative_to(root).as_posix())
    for file_path in paths:
        if file_path.is_dir():
            continue

        # Add file path
        sha.update(file_path.relative_to(root).as_posix().encode('utf-8'))

        # Add content hash
        sha.update(hash_file(file_path).encode('utf-8'))

    return sha.hexdigest()


def validate_dir(
        root,  # type: Union[Text, Path]
        dir_hash,  # type: Text
        exclude=None  # type: Optional[Iterable[Text]]
):
    # type: (...) -> bool
    """Check if directory hash is the same as provided"""

    return Path(root).is_dir() and hash_dir(root, exclude=exclude) == dir_hash
