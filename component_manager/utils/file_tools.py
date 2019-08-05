"""Set of tools and constants to work with files and directories """
import fnmatch
import re
from typing import Any, Callable, List, Pattern, Set

IGNORED_DIRS = ['.git', '__pycache__']
IGNORED_FILES = ['*.pyc', '*.pyd', '*.pyo', '.DS_Store']

ignored_dirs_re = re.compile(r"|".join([fnmatch.translate(x) for x in IGNORED_DIRS]) or r"$.")
ignored_files_re = re.compile(r"|".join([fnmatch.translate(x) for x in IGNORED_FILES]) or r"$.")


def copytree_ignore(
        ignored_dirs_re=ignored_dirs_re,
        ignored_files_re=ignored_files_re,
):  # type: (Pattern[str], Pattern[str]) -> Callable[[Any, List[str]], Set[str]]
    def filter(dir, files):  # type: (str, List[str]) -> Set[str]
        # ignore current dir
        if ignored_dirs_re.match(dir):
            return set([])

        # ignore files and sub-dirs
        return set([f for f in files if not ignored_files_re.match(f) and not ignored_dirs_re.match(f)])

    return filter
