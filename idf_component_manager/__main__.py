#!/usr/bin/env python
#
# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import argparse
import os
import sys
import warnings

from idf_component_manager.utils import print_error, showwarning
from idf_component_tools.errors import FatalError

from . import version
from .core import ComponentManager

KNOWN_ACTIONS = [
    'pack-component',
    'upload-component',
    'upload-component-status',
    'create-project-from-example',
    'delete-version',
]


def check_required_args(args, required_field=None):
    required_field = required_field or []

    for _f in required_field:
        if getattr(args, _f) is None:
            raise ValueError('--{} is required'.format(_f.replace('_', '-')))


def main(command_args=None):  # type: (list[str] | None) -> None
    parser = argparse.ArgumentParser(description='IDF component manager v{}'.format(version))
    parser.add_argument('command', choices=KNOWN_ACTIONS, help='Command to execute')
    parser.add_argument(
        '--path',
        help='Working directory (default: current directory).',
        default=os.getcwd(),
    )
    parser.add_argument(
        '--namespace', help='Namespace for the component. Can be set in the config file.'
    )
    parser.add_argument(
        '--service-profile',
        help='Profile for the component registry to use. '
        'By default profile named "default" will be used.',
        default='default',
    )
    parser.add_argument('--name', help='Component name.')
    parser.add_argument('--archive', help='Path of the archive with component to upload.')
    parser.add_argument('--job', help='Background job ID.')
    parser.add_argument('--version', help='Version for upload or deletion.')
    parser.add_argument(
        '--skip-pre-release',
        help='Do not upload pre-release versions.',
        action='store_true',
    )
    parser.add_argument(
        '--check-only',
        help='Check if given component version is already uploaded and exit.',
        action='store_true',
    )
    parser.add_argument(
        '--allow-existing',
        help='Return success if existing version is already uploaded.',
        action='store_true',
    )
    parser.add_argument('--example', help='Example name.')

    args = parser.parse_args(args=command_args)

    try:
        warnings.showwarning = showwarning
        manager = ComponentManager(args.path)

        if args.command == 'pack-component':
            warnings.warn(
                'Deprecated! New CLI command: "compote component pack"',
                DeprecationWarning,
            )
            check_required_args(args, ['name', 'version'])
            manager.pack_component(name=args.name, version=args.version)
        elif args.command == 'upload-component':
            warnings.warn(
                'Deprecated! New CLI command: "compote component upload"',
                DeprecationWarning,
            )
            check_required_args(args, ['name'])
            manager.upload_component(
                name=args.name,
                version=args.version,
                service_profile=args.service_profile,
                namespace=args.namespace,
                archive=args.archive,
                skip_pre_release=args.skip_pre_release,
                check_only=args.check_only,
                allow_existing=args.allow_existing,
            )
        elif args.command == 'upload-component-status':
            warnings.warn(
                'Deprecated! New CLI command: "compote component upload-status"',
                DeprecationWarning,
            )
            check_required_args(args, ['job'])
            manager.upload_component_status(job_id=args.job, service_profile=args.service_profile)
        elif args.command == 'create-project-from-example':
            warnings.warn(
                'Deprecated! New CLI command: "compote project create-from-example"',
                DeprecationWarning,
            )
            check_required_args(args, ['namespace', 'name', 'example', 'version'])
            example = '{}/{}={}:{}'.format(args.namespace, args.name, args.version, args.example)
            manager.create_project_from_example(example=example)
        elif args.command == 'delete-version':
            warnings.warn(
                'Deprecated! New CLI command: "compote component delete"',
                DeprecationWarning,
            )
            check_required_args(args, ['name', 'version'])
            manager.delete_version(
                name=args.name,
                version=args.version,
                service_profile=args.service_profile,
                namespace=args.namespace,
            )
    except FatalError as e:
        print_error(e)
        sys.exit(e.exit_code)


if __name__ == '__main__':
    main()
