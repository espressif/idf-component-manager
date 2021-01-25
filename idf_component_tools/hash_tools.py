"""Tools for hashing and hash validation for whole packages"""
import json
import os
from hashlib import sha256
from io import open
from typing import Any, Pattern, Text

from .file_tools import ignored_dirs_re, ignored_files_re

BLOCK_SIZE = 65536


def hash_object(obj):  # type: (Any) -> str
    """Calculate sha256 of passed json-serialisable object"""
    sha = sha256()
    sha.update(json.dumps(obj, sort_keys=True, separators=(',', ':')).encode())
    return sha.hexdigest()


def hash_file(file_path):  # type: (Text) -> str
    """Calculate sha256 of file"""
    sha = sha256()

    with open(file_path, 'rb') as f:
        while True:
            block = f.read(BLOCK_SIZE)
            if not block:
                break
            sha.update(block)

    return sha.hexdigest()


def hash_dir(
        root,  # type: Text
        ignored_dirs_re=ignored_dirs_re,  # type: Pattern[str]
        ignored_files_re=ignored_files_re  # type: Pattern[str]
):  # type: (...) -> str
    """Calculate sha256 of sha256 of all files and file names.
    Simlinks are not followed.
    """
    sha = sha256()

    for current_dir, dirs, files in os.walk(root, topdown=True):
        # ignore dirs
        dirs[:] = [d for d in dirs if not ignored_dirs_re.match(d)]

        # ignore files
        files = [f for f in files if not ignored_files_re.match(f)]

        for file_name in files:

            # Add file path
            file_path = os.path.join(os.path.relpath(current_dir, root), file_name)
            sha.update(file_path.encode('utf-8'))

            # Add content hash
            full_path = os.path.join(current_dir, file_name)
            sha.update(hash_file(full_path).encode('utf-8'))

    return sha.hexdigest()


def validate_dir(
        root,  # type: Text
        dir_hash,  # type: Text
        ignored_dirs_re=ignored_dirs_re,  # type: Pattern[str]
        ignored_files_re=ignored_files_re  # type: Pattern[str]
):
    # type: (...) -> bool
    """Check if directory hash is the same as provided"""

    return os.path.isdir(root) and hash_dir(root, ignored_dirs_re, ignored_files_re) == dir_hash
