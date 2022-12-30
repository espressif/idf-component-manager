# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import click

from idf_component_manager.utils import print_info
from idf_component_tools.file_cache import FileCache
from idf_component_tools.file_tools import human_readable_size


@click.group()
def cache():
    """
    Group of cache related commands
    """
    pass


@cache.command()
def clear():
    """
    Clear cache of components and API client cache
    """
    FileCache().clear()
    print_info('Successfully cleared cache at\n\t{}'.format(FileCache().path()))


@cache.command()
def path():
    """
    Print cache path
    """
    print_info(FileCache().path())


@cache.command()
@click.option('--bytes', is_flag=True, default=False, help='Print size in bytes')
def size(bytes):
    """
    Print cache size of cache in human readable format
    """
    size = FileCache().size()
    if bytes:
        print_info(str(size))
    else:
        print_info(human_readable_size(size))
