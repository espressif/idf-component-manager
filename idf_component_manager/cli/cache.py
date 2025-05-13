# SPDX-FileCopyrightText: 2022-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import click

from idf_component_tools import notice
from idf_component_tools.file_cache import FileCache
from idf_component_tools.file_tools import human_readable_size


def init_cache():
    @click.group()
    def cache():
        """
        Group of commands for managing the cache of the IDF Component Manager.
        """
        pass

    @cache.command()
    def clear():
        """
        Clear the component cache.
        """
        FileCache().clear()
        notice(f'Successfully cleared cache at\n\t{FileCache().path()}')

    @cache.command()
    def path():
        """
        Print the cache path.
        """
        print(FileCache().path())

    @cache.command()
    @click.option('--bytes', is_flag=True, default=False, help='Print size in bytes')
    def size(bytes):
        """
        Print the cache size in a human-readable format.
        """
        size = FileCache().size()
        if bytes:
            print(str(size))
        else:
            print(human_readable_size(size))

    return cache
