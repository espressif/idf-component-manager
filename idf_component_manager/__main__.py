#!/usr/bin/env python

import argparse
import os
import sys

from idf_component_tools.errors import FatalError

from . import version
from .core import ComponentManager

KNOWN_ACTIONS = [
    'pack-component',
    'upload-component',
    'upload-component-status',
    'delete-version',
]


def main():
    parser = argparse.ArgumentParser(description='IDF component manager v{}'.format(version))
    parser.add_argument('command', choices=KNOWN_ACTIONS, help='Command to execute')
    parser.add_argument('--path', help='Working directory (default: current directory).', default=os.getcwd())
    parser.add_argument('--namespace', help='Namespace for the component. Can be set in config file.')
    parser.add_argument(
        '--service-profile',
        help='Profile for component registry to use. By default profile named "default" will be used.',
        default='default',
    )
    parser.add_argument('--name', help='Component name', required=True)
    parser.add_argument('--archive', help='Path of the archive with component to upload.')
    parser.add_argument('--job', help='Background job ID.')
    parser.add_argument('--version', help='Version for upload or deletion.')
    parser.add_argument('--skip-pre-release', help='Do not upload pre-release versions.', action='store_true')
    parser.add_argument(
        '--check-only', help='Check if given component version is already uploaded and exit.', action='store_true')
    parser.add_argument(
        '--allow-existing', help='Return success if existing version is already uploaded.', action='store_true')

    args = parser.parse_args()

    try:
        manager = ComponentManager(args.path)
        getattr(manager, str(args.command).replace('-', '_'))(vars(args))
    except FatalError as e:
        print(e)
        sys.exit(e.exit_code)


if __name__ == '__main__':
    main()
