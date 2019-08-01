"""Tools for hashing and hash validation for whole packages"""
import fnmatch
import json
import os
import re
from hashlib import sha256
from typing import Any, List, Text


class HashTools:
    """Tools for sha256 manipulation"""

    BLOCK_SIZE = 65536
    IGNORED_DIRS = ['.git', '__pycache__']
    IGNORED_FILES = ['*.pyc', '*.pyd', '*.pyo', '.DS_Store']

    @classmethod
    def hash_object(cls, obj):  # type: (Any) -> str
        """Calculate sha256 of passed json-serialisable object"""
        sha = sha256()
        sha.update(json.dumps(obj, sort_keys=True, separators=(',', ':')).encode())
        return sha.hexdigest()

    @classmethod
    def hash_file(cls, file_path):  # type: (Text) -> str
        """Calculate sha256 of file"""
        sha = sha256()

        with open(file_path, 'rb') as f:
            while True:
                block = f.read(cls.BLOCK_SIZE)
                if not block:
                    break
                sha.update(block)

        return sha.hexdigest()

    @classmethod
    def hash_dir(
            cls,
            root,  # type: Text
            ignored_dirs=IGNORED_DIRS,  # type: List[str]
            ignored_files=IGNORED_FILES  # type: List[str]
    ):  # type: (...) -> str
        """Calculate sha256 of sha256 of all files and file names.
        Simlinks are not followed.
        """
        sha = sha256()

        ignored_dirs_re = re.compile(r"|".join([fnmatch.translate(x) for x in ignored_dirs]) or r"$.")
        ignored_files_re = re.compile(r"|".join([fnmatch.translate(x) for x in ignored_files]) or r"$.")

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
                sha.update(cls.hash_file(full_path).encode('utf-8'))

        return sha.hexdigest()

    @classmethod
    def validate_dir(
            cls,
            root,  # type: Text
            hash,  # type: Text
            ignored_dirs=IGNORED_DIRS,  # type: List[str]
            ignored_files=IGNORED_FILES  # type: List[str]
    ):
        # type: (...) -> bool
        """Check if directory hash is the same as provided"""

        return os.path.isdir(root) and cls.hash_dir(root, ignored_dirs, ignored_files) == hash
