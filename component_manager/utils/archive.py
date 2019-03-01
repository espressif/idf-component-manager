"""Set of tools to work with archives"""

import os
import re
from shutil import get_archive_formats


class ArchiveError(RuntimeError):
    pass


def get_format_from_path(path):
    """ Returns tuple of format and extension or None"""

    if re.search(r"(\.tar\.gz$)|(\.tgz$)", path):
        return ("gztar", "tgz")
    elif path.endswith(".zip"):
        return ("zip", "zip")
    elif re.search(r"(\.tar\.bz2$)|(\.tbz2$)", path):
        return ("bztar", "tbz2")
    elif re.search(r"(\.tar\.xz$)|(\.txz$)", path):
        return ("xztar", "txz")
    elif path.endswith(".tar"):
        return ("tar", "tar")
    else:
        return None


def is_known_format(fmt):
    for known_format in get_archive_formats():
        if fmt == known_format[0]:
            return True

    return False
