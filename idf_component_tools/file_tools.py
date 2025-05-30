# SPDX-FileCopyrightText: 2022-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
"""Set of tools and constants to work with files and directories"""

import os
import shutil
import tempfile
import typing as t
from pathlib import Path
from shutil import copytree, rmtree

from idf_component_tools.errors import FatalError
from idf_component_tools.git_client import GitClient
from idf_component_tools.messages import warn

DEFAULT_EXCLUDE = [
    # Python files
    '**/__pycache__',
    '**/*.pyc',
    '**/*.pyd',
    '**/*.pyo',
    # macOS files
    '**/.DS_Store',
    # Git
    '**/.git/**/*',
    # SVN
    '**/.svn/**/*',
    # dist and build artifacts
    '**/dist/**/*',
    '**/build/**/*',
    # idf-build-apps artifacts
    '**/build_*/**/*',
    # artifacts from example projects
    '**/managed_components/**/*',
    '**/dependencies.lock',
    # CI files
    '**/.github/**/*',
    '**/.gitlab-ci.yml',
    # IDE files
    '**/.idea/**/*',
    '**/.vscode/**/*',
    # Configs
    '**/.settings/**/*',
    '**/sdkconfig',
    '**/sdkconfig.old',
    # Hash file
    '**/.component_hash',
]

UNEXPECTED_FILES = {
    'CMakeCache.txt',
}


def get_file_extension(path: str) -> t.Optional[str]:
    """Returns file extension with leading dot or None"""

    extensions = Path(path).suffixes

    if not extensions:
        return None

    # Join multiple extensions (for example .tar.gz)
    return ''.join(extensions)


def gitignore_ignored_files(path: t.Union[str, Path]) -> t.Set[Path]:
    """Returns set of files ignored by .gitignore file"""

    base_path = Path(path)
    paths = set()

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir_path = Path(tmp_dir)

        # Create git client instance
        git_client = GitClient(
            work_tree=str(base_path.resolve()), git_dir=str(tmp_dir_path.resolve())
        )

        # Create a new empty repository
        git_client.init_empty_repository()
        ignored_files = git_client.ignored_files()

        for file in ignored_files:
            paths.add(base_path / Path(file))

    return paths


def filtered_paths(
    path: t.Union[str, Path],
    use_gitignore: bool = False,
    include: t.Optional[t.Iterable[str]] = None,
    exclude: t.Optional[t.Iterable[str]] = None,
    exclude_default: bool = True,
) -> t.Set[Path]:
    """Returns set of paths that should be included in component archive.

    There are two ways to filter paths:

    1. If `use_gitignore` is True, then `.gitignore` files will be used to exclude files.
    If `exclude` is set, it will be used to exclude files by default before applying `.gitignore` patterns.
    Option `exclude_default` is ignored in this case.

    2. Overwise, `include` and `exclude` will be used to filter files.
    If `exclude_default` is True, then default patterns will also be applied.
    """

    if include is None:
        include = set()

    if exclude is None:
        exclude = set()

    base_path = Path(path)
    paths: t.Set[Path] = set()

    def include_paths(pattern):
        paths.update(base_path.glob(pattern))

    def exclude_paths(pattern):
        paths.difference_update(base_path.glob(pattern))

    def exclude_all_directories():
        for path in list(paths):
            if path.is_dir():
                paths.remove(path)

    # First include everything
    include_paths('**/*')

    if use_gitignore:
        # Exclude .gitignore patterns
        exclude_gitignore = gitignore_ignored_files(base_path)
        paths.difference_update(exclude_gitignore)
        exclude_all_directories()
    else:
        # Exclude defaults
        if exclude_default:
            for pattern in DEFAULT_EXCLUDE:
                exclude_paths(pattern)

    # Exclude manifest patterns
    for pattern in exclude:
        exclude_paths(pattern)

    exclude_all_directories()

    # Include manifest patterns
    for pattern in include:
        include_paths(pattern)

    return paths


def prepare_empty_directory(directory: str) -> None:
    """Prepare directory empty"""
    dir_exist = os.path.exists(directory)

    # Delete path if it's not empty
    if dir_exist and os.listdir(directory):
        rmtree(directory)
        dir_exist = False

    if not dir_exist:
        try:
            os.makedirs(directory)
        except NotADirectoryError:
            raise FatalError(f'Not a directory in the path. Cannot create directory: {directory}')
        except PermissionError:
            raise FatalError(f'Permission denied. Cannot create directory: {directory}')


def copy_directory(source_directory: str, destination_directory: str) -> None:
    if os.path.exists(destination_directory):
        rmtree(destination_directory)
    copytree(source_directory, destination_directory)


def copy_directories(
    source_directory: str, destination_directory: str, paths: t.Iterable[Path]
) -> None:
    for path in sorted(paths):
        path = str(path)  # type: ignore # Path backward compatibility
        rel_path = os.path.relpath(path, source_directory)
        dest_path = os.path.join(destination_directory, rel_path)

        if os.path.isfile(path):
            dest_dir = os.path.dirname(dest_path)

            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir)

            shutil.copy2(path, dest_path)
        else:
            os.makedirs(dest_path)


def copy_filtered_directory(
    source_directory: str,
    destination_directory: str,
    use_gitignore: bool = False,
    include: t.Optional[t.Iterable[str]] = None,
    exclude: t.Optional[t.Iterable[str]] = None,
) -> None:
    paths = filtered_paths(
        source_directory, use_gitignore=use_gitignore, include=include, exclude=exclude
    )
    prepare_empty_directory(destination_directory)
    copy_directories(source_directory, destination_directory, paths)


def check_unexpected_component_files(path: t.Union[str, Path]) -> None:
    """Create a warning if a directory contains files not expected inside component"""
    for root, _dirs, files in os.walk(str(path)):
        unexpected_files = UNEXPECTED_FILES.intersection(files)
        if unexpected_files:
            warn(
                'Unexpected files "{files}" found in the component directory "{path}". '
                'Please check if these files should be ignored'.format(
                    files=', '.join(unexpected_files), path=os.path.relpath(root, start=str(path))
                )
            )


def directory_size(dir_path: str) -> int:
    """Return the total size of all files in the directory tree"""
    total_size = 0
    directory = Path(dir_path)
    for file in directory.glob('**/*'):
        try:
            total_size += os.stat(str(file)).st_size
        except OSError:
            pass
    return total_size


def human_readable_size(size: int) -> str:
    """Return a human readable string representation of a data size"""
    if size < 0:
        raise ValueError('size must be non-negative')

    if size < 1024:
        return '{} bytes'.format(size)

    if size < 1024**2:
        return '{:.2f} KB'.format(size / 1024.0)

    if size < 1024**3:
        return '{:.2f} MB'.format(size / (1024.0**2))

    return '{:.2f} GB'.format(size / (1024.0**3))
