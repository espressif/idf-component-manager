"""Set of tools and constants to work with files and directories """
import os
from pathlib import Path
from shutil import rmtree

try:
    from typing import Callable, Iterable, Optional, Set, Text, Union
except ImportError:
    pass

DEFAULT_INCLUDE = ['**/*']
DEFAULT_EXCLUDE = [
    # Python files
    '**/__pycache__',
    '**/*.pyc',
    '**/*.pyd',
    '**/*.pyo',
    # macOS files
    '**/.DS_Store',
    # Git
    '**/.git',
    # dist and build artefacts
    './dist/**/*',
    'build/**/*',
    # CI files
    '.github/**/*',
    '.gitlab-ci.yml',
    # IDE files
    '.idea/**/*',
    '.vscode/**/*',
    # Configs
    '.settings/**/*',
    '**/sdkconfig',
]


def filtered_paths(path, include=None, exclude=None):
    # type: (Union[Text, Path], Optional[Iterable[str]], Optional[Iterable[str]]) -> Set[Path]
    if include is None:
        include = DEFAULT_INCLUDE

    if exclude is None:
        exclude = DEFAULT_EXCLUDE

    base_path = Path(path)

    paths = set()  # type: Set[Path]

    for pattern in include:
        paths.update(base_path.glob(pattern))

    for pattern in exclude:
        paths.difference_update(base_path.glob(pattern))

    return paths


def filter_builder(paths):  # type: (Iterable[Path]) -> Callable[[Path], bool]
    def filter_path(path):  # type: (Path) -> bool
        '''Returns True if path should be included, False otherwise'''
        return path.resolve() in paths

    return filter_path


def create_directory(directory):  # type: (str) -> None
    """Create directory, if doesn't exist yet"""
    if not os.path.exists(directory):
        os.makedirs(directory)


def prepare_empty_directory(directory):  # type: (str) -> None
    """Prepare directory empty"""
    dir_exist = os.path.exists(directory)

    # Delete path if it's not empty
    if dir_exist and os.listdir(directory):
        rmtree(directory)
        dir_exist = False

    if not dir_exist:
        os.makedirs(directory)
