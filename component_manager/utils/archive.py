"""Set of tools to work with archives"""

import os
import re
from shutil import get_archive_formats, rmtree


class ArchiveError(RuntimeError):
    pass


def get_format_from_path(path):
    """ Returns tuple of format , extension, unpacking function or None"""

    if re.search(r"(\.tar\.gz$)|(\.tgz$)", path):
        return ('gztar', 'tgz', unpack_tar)
    elif path.endswith('.zip'):
        return ('zip', 'zip', unpack_zip)
    elif re.search(r"(\.tar\.bz2$)|(\.tbz2$)", path):
        return ('bztar', 'tbz2', unpack_tar)
    elif re.search(r"(\.tar\.xz$)|(\.txz$)", path):
        return ('xztar', 'txz', unpack_tar)
    elif path.endswith('.tar'):
        return ('tar', 'tar', unpack_tar)
    else:
        raise ArchiveError('Unknown archive extension for path: %s' % path)


def is_known_format(fmt):
    for known_format in get_archive_formats():
        if fmt == known_format[0]:
            return True

    return False


def _prepare_empty_directory(directory):
    """Prepare directory"""
    dir_exist = os.path.exists(directory)

    # Delete path if it's not empty
    if dir_exist and os.listdir(directory):
        rmtree(directory)
        dir_exist = False

    if not dir_exist:
        os.makedirs(directory)


def unpack_tar(file, destination_directory):
    """Unpack .(tar.|t)(xz|gz|bz2) file"""
    import tarfile

    try:
        tar = tarfile.open(file)
        _prepare_empty_directory(destination_directory)
    except tarfile.TarError:
        raise ArchiveError('%s is not a valid tar archive' % file)

    try:
        tar.extractall(destination_directory)
    finally:
        tar.close()


def unpack_zip(file, destination_directory):
    """Unpack zip file"""
    import zipfile

    if not zipfile.is_zipfile(file):
        raise ArchiveError('%s is not a zip file' % file)

    _prepare_empty_directory(destination_directory)

    with zipfile.ZipFile(file) as zip:
        for item in zip.infolist():
            zip.extract(item, destination_directory)


def unpack_archive(file, destination_directory):
    _prepare_empty_directory(destination_directory)
    format, ext, handler = get_format_from_path(file)
    if not is_known_format(format):
        raise ArchiveError('.%s files are not supported on your system' % ext)
    handler(file, destination_directory)
