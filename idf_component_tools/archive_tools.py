"""Set of tools to work with archives"""

import os
import re
from shutil import get_archive_formats

from .file_tools import prepare_empty_directory


class ArchiveError(RuntimeError):
    pass


KNOWN_MIME_TYPES = [
    'application/x-tar',
    'application/x-gtar',
    'application/zip',
    'application/gzip',
    'application/tar+gzip',
    'application/octet-stream',
]

KNOWN_ARCHIVE_EXTENSIONS = [
    'tar.bz2',
    'tar.gz',
    'tar.xz',
    'tar',
    'tbz2',
    'tgz',
    'txz',
    'zip',
]


def get_format_from_path(path):
    """ Returns tuple of format , extension, unpacking function or None"""

    if re.search(r'(\.tar\.gz$)|(\.tgz$)', path):
        return ('gztar', 'tgz', unpack_tar)
    elif path.endswith('.zip'):
        return ('zip', 'zip', unpack_zip)
    elif re.search(r'(\.tar\.bz2$)|(\.tbz2$)', path):
        return ('bztar', 'tbz2', unpack_tar)
    elif re.search(r'(\.tar\.xz$)|(\.txz$)', path):
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


def unpack_tar(file, destination_directory):
    """Unpack .(tar.|t)(xz|gz|bz2) file"""
    import tarfile

    try:
        tar = tarfile.open(file)
        prepare_empty_directory(destination_directory)
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

    prepare_empty_directory(destination_directory)

    with zipfile.ZipFile(file) as zip:
        for item in zip.infolist():
            zip.extract(item, destination_directory)


def unpack_archive(file, destination_directory):
    prepare_empty_directory(destination_directory)
    format, ext, handler = get_format_from_path(file)
    if not is_known_format(format):
        raise ArchiveError('.%s files are not supported on your system' % ext)
    handler(file, destination_directory)


def pack_archive(source_directory, destination_directory, filename, filter=None):
    # Create tar+gzip archive
    import tarfile
    archive_path = os.path.join(destination_directory, filename)
    prepare_empty_directory(destination_directory)
    with tarfile.open(archive_path, 'w:gz') as archive:
        archive.add(source_directory, arcname='.', filter=filter)
