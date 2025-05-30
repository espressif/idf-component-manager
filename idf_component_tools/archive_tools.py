# SPDX-FileCopyrightText: 2022-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
"""Set of tools to work with archives"""

import re
import tarfile
import typing as t
from pathlib import Path
from shutil import get_archive_formats

from .errors import FatalError
from .file_tools import prepare_empty_directory


class ArchiveError(FatalError):
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


def get_archive_extension(filename: str) -> t.Optional[str]:
    """Get archive extension from filename.

    :param filename: archive filename
    :return: extension or None
    """
    try:
        return f'.{get_format_from_path(filename)[1]}'
    except ArchiveError:
        return None


def get_format_from_path(path):
    """Returns tuple of format , extension, unpacking function or None"""

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
        raise ArchiveError(f'Unknown archive extension for path: {path}')


def is_known_format(fmt):
    for known_format in get_archive_formats():
        if fmt == known_format[0]:
            return True

    return False


def unpack_tar(file, destination_directory):
    """Unpack .(tar.|t)(xz|gz|bz2) file"""
    try:
        tar = tarfile.open(file)
        prepare_empty_directory(destination_directory)
    except tarfile.TarError:
        raise ArchiveError(f'{file} is not a valid tar archive')

    try:
        tar.extractall(destination_directory)  # noqa: S202
    finally:
        tar.close()


def unpack_zip(file, destination_directory):
    """Unpack zip file"""
    import zipfile

    if not zipfile.is_zipfile(file):
        raise ArchiveError(f'{file} is not a zip file')

    prepare_empty_directory(destination_directory)

    with zipfile.ZipFile(file) as archive:
        for item in archive.infolist():
            archive.extract(item, destination_directory)


def unpack_archive(file: t.Union[str, Path], destination_directory: str) -> None:
    prepare_empty_directory(destination_directory)
    archive_format, ext, handler = get_format_from_path(file)
    if not is_known_format(archive_format):
        raise ArchiveError(f'.{ext} files are not supported on your system')
    handler(file, destination_directory)


def pack_archive(source_dir: t.Union[str, Path], archive_filepath: str) -> None:
    """Create tar+gzip archive"""
    try:
        with tarfile.open(archive_filepath, 'w:gz') as archive:
            archive.add(source_dir, arcname='')
    except tarfile.TarError:
        raise ArchiveError(f'{archive_filepath} is not a valid tar archive')
