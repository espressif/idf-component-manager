"""Set of tools and constants to work with files and directories """
import fnmatch
import os
import re
from pathlib import Path
from shutil import rmtree

try:
    from typing import Any, Callable, Iterable, List, Optional, Pattern, Set
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
    './build/**/*',
]

IGNORED_DIRS = ['.git', '__pycache__']
IGNORED_FILES = ['*.pyc', '*.pyd', '*.pyo', '.DS_Store']

ignored_dirs_re = re.compile(r'|'.join([fnmatch.translate(x) for x in IGNORED_DIRS]) or r'$.')
ignored_files_re = re.compile(r'|'.join([fnmatch.translate(x) for x in IGNORED_FILES]) or r'$.')


def filtered_paths(path, include=None, exclude=None):
    # type: (str, Optional[Iterable[str]], Optional[Iterable[str]]) -> Set[Path]
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


def copytree_ignore_builder(
    ignored_dirs_re=ignored_dirs_re,
    ignored_files_re=ignored_files_re,
):  # type: (Pattern[str], Pattern[str]) -> Callable[[Any, List[str]], Set[str]]
    '''Builds a filter function shutil.copytree'''
    def filter_path(src, names):  # type: (str, List[str]) -> Set[str]
        '''
        `src` is a parameter, which is the directory being visited by copytree(),
        and `names` which is the list of `src` contents, as returned by os.listdir()
        '''
        # ignore current dir
        if ignored_dirs_re.match(src):
            return set([])

        # ignore files and sub-dirs
        return set([f for f in names if not ignored_files_re.match(f) and not ignored_dirs_re.match(f)])

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
