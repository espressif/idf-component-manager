# SPDX-FileCopyrightText: 2023-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import re
import typing as t
from pathlib import Path

from idf_component_tools.file_tools import filtered_paths
from idf_component_tools.manager import ManifestManager

from .calculate import hash_dir, hash_file
from .checksums import ChecksumsManager, ChecksumsModel
from .constants import CHECKSUMS_FILENAME, HASH_FILENAME, SHA256_RE
from .errors import (
    ComponentNotFoundError,
    HashDictEmptyError,
    HashNotEqualError,
    HashNotFoundError,
    HashNotSHA256Error,
)


def is_hash_valid(hash):
    """Check if provided hash is a valid SHA256 hash.

    :param hash: Hash to check
    :return: True if hash is valid, False otherwise
    """

    return re.match(SHA256_RE, hash)


def validate_hash_eq_hashfile(root: t.Union[str, Path], expected_hash: str) -> None:
    """Validate expected hash against hash of the component stored in the hash file.

    :param root: Path to the component
    :param expected_hash: Expected hash of the component
    :raises ComponentNotFoundError: Component path does not exist
    :raises HashNotFoundError: Hash file does not exist
    :raises HashNotSHA256Error: Hash is not a valid SHA256 hash
    :raises HashNotEqualError: Hash does not match expected hash
    """

    root_path = Path(root)

    if not root_path.exists():
        raise ComponentNotFoundError(f'Component path "{root}" does not exist')

    hash_path = root_path / HASH_FILENAME
    if not hash_path.exists():
        raise HashNotFoundError(f'Hash file "{hash_path}" does not exist')

    with open(hash_path, encoding='utf-8') as f:
        hash_from_file = f.read().strip()

    if not is_hash_valid(hash_from_file):
        raise HashNotSHA256Error(f'Hash "{hash_from_file}" is not a valid SHA256 hash')

    if hash_from_file != expected_hash:
        raise HashNotEqualError(
            f'Hash "{hash_from_file}" does not match expected hash "{expected_hash}"'
        )


def validate_hashfile_eq_hashdir(root: t.Union[str, Path]) -> None:
    """Validate component hash stored in the certain file against hash of the component directory.

    In order to support backward compatibility, there are 2 ways to validate component integrity:

    1. Validate hash of each file in the component directory, if CHECKSUMS_FILENAME is present
    2. Validate hashsum of the component directory, if HASH_FILENAME is present

    :param root: Path to the component
    :raises ComponentNotFoundError: Component path does not exist
    :raises HashNotFoundError: Hash file does not exist
    """

    root_path = Path(root)

    if not root_path.exists():
        raise ComponentNotFoundError(f'Component path "{root}" does not exist')

    checksums_manager = ChecksumsManager(root_path)
    hash_path = root_path / HASH_FILENAME

    if checksums_manager.exists():
        expected_checksums = checksums_manager.load()
        validate_checksums_eq_hashdir(root, expected_checksums)
    elif hash_path.exists():
        with open(hash_path, encoding='utf-8') as f:
            expected_hash = f.read().strip()

        validate_hash_eq_hashdir(root, expected_hash)
    else:
        raise HashNotFoundError(f'Hash file does not exist in "{root}"')


def validate_hash_eq_hashdir(root: t.Union[str, Path], expected_hash: str) -> None:
    """Validate expected hash against hashsum of the component directory.

    :param root: Path to the component
    :param expected_hash: Expected hash of the component
    :raises HashNotEqualError: Hash does not match expected hash
    """

    manifest_manager = ManifestManager(root, 'test')
    manifest = manifest_manager.load()

    exclude_set = set(manifest.exclude_set)
    exclude_set.add(f'**/{HASH_FILENAME}')
    exclude_set.add(f'**/{CHECKSUMS_FILENAME}')

    is_valid = validate_dir(
        root,
        expected_hash,
        use_gitignore=manifest.use_gitignore,
        include=manifest.include_set,
        exclude=exclude_set,
        exclude_default=False,
    )

    if not is_valid:
        raise HashNotEqualError(
            f'Hash of the component in "{root}" does not match expected hash "{expected_hash}"'
        )


def validate_checksums_eq_hashdir(
    root: t.Union[str, Path], expected_checksums: ChecksumsModel
) -> None:
    """Validate hash of each file in the component directory.

    Compares hash of each file provided in the dictionary against the actual hash of the file in the component directory.

    :param root: Path to the component
    :param expected_checksums: Expected checksums.
    :raises ComponentNotFoundError: Component path does not exist
    :raises HashDictEmptyError: Dictionary of expected files hash is empty
    :raises HashNotSHA256Error: Some hash is not a valid SHA256 hash
    :raises HashNotEqualError: Some hash does not match expected hash or component files are different
    """

    root_path = Path(root)

    if not root_path.exists():
        raise ComponentNotFoundError(f'Component path "{root}" does not exist')

    if len(expected_checksums.files) == 0:
        raise HashDictEmptyError()

    for expected_file in expected_checksums.files:
        expected_file_path = root_path / expected_file.path
        if not is_hash_valid(expected_file.hash):
            raise HashNotSHA256Error(
                f'Hash "{expected_file.hash}" for file "{expected_file_path}" is not a valid SHA256 hash'
            )

    manifest_manager = ManifestManager(root, 'test')
    manifest = manifest_manager.load()

    exclude_set = set(manifest.exclude_set)
    exclude_set.add(f'**/{HASH_FILENAME}')
    exclude_set.add(f'**/{CHECKSUMS_FILENAME}')

    paths = sorted(
        filtered_paths(
            root,
            use_gitignore=manifest.use_gitignore,
            include=manifest.include_set,
            exclude=exclude_set,
            exclude_default=False,
        ),
        key=lambda path: path.relative_to(root).as_posix(),
    )

    for expected_file in expected_checksums.files:
        expected_file_path = root_path / expected_file.path

        if expected_file_path not in paths:
            raise HashNotEqualError(
                f'File "{expected_file.path}" is missing in the component in "{root}"'
            )

        hash = hash_file(expected_file_path)

        if hash != expected_file.hash:
            raise HashNotEqualError(
                f'Hash of the file "{expected_file.path}" in the component in "{root}" does not match expected hash "{expected_file.hash}"'
            )


def validate_dir(
    root: t.Union[str, Path],
    dir_hash: str,
    use_gitignore: bool = False,
    include: t.Optional[t.Iterable[str]] = None,
    exclude: t.Optional[t.Iterable[str]] = None,
    exclude_default: bool = True,
) -> bool:
    """Validate directory hash.

    :param root: Path to the component
    :param dir_hash: Expected hash of the directory
    :param use_gitignore: Use .gitignore file, defaults to False
    :param include: List of paths to include, defaults to None
    :param exclude: List of paths to exclude, defaults to None
    :param exclude_default: List of paths to exclude by default, defaults to True
    :return: True if hash is valid, False otherwise
    """

    current_hash = Path(root).is_dir() and hash_dir(
        root,
        use_gitignore=use_gitignore,
        include=include,
        exclude=exclude,
        exclude_default=exclude_default,
    )

    return current_hash == dir_hash
