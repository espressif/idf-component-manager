#!/usr/bin/env python
#
# SPDX-FileCopyrightText: 2019-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
#
# 'prepare.py' is a tool to be used by CMake build system to prepare components
# from package manager

import argparse
import os
import sys
import typing as t

from idf_component_manager.core import ComponentManager
from idf_component_tools import error, setup_logging, warn
from idf_component_tools.debugger import KCONFIG_CONTEXT
from idf_component_tools.errors import FatalError
from idf_component_tools.manifest import ComponentRequirement


def _component_list_file(build_dir):
    return os.path.join(build_dir, 'components_with_manifests_list.temp')


def prepare_dep_dirs(args):
    if args.sdkconfig_json_file:
        KCONFIG_CONTEXT.get().update_from_file(args.sdkconfig_json_file)

    build_dir = args.build_dir or os.path.dirname(args.managed_components_list_file)
    ComponentManager(
        args.project_dir,
        lock_path=args.lock_path,
        interface_version=args.interface_version,
    ).prepare_dep_dirs(
        managed_components_list_file=args.managed_components_list_file,
        component_list_file=_component_list_file(build_dir),
        local_components_list_file=args.local_components_list_file,
    )

    kconfig_ctx = KCONFIG_CONTEXT.get()
    if kconfig_ctx.missed_keys:
        debug_strs: t.Set[str] = set()

        def debug_message(req: ComponentRequirement) -> str:
            return 'introduced by {}, defined in {}'.format(
                req.name,
                req._manifest_manager.path if req._manifest_manager else '(unknown)',
            )

        for key, reqs in kconfig_ctx.missed_keys.items():
            for req in reqs:
                debug_strs.add(f'    {key}, {debug_message(req)}')

        _nl = '\n'
        warn(
            f'The following Kconfig variables were used in "if" clauses, but not found in any Kconfig file:\n'
            f'{_nl.join(sorted(debug_strs))}\n'
        )
        exit(10)


def inject_requirements(args):
    if args.sdkconfig_json_file:
        KCONFIG_CONTEXT.get().update_from_file(args.sdkconfig_json_file)

    ComponentManager(
        args.project_dir,
        lock_path=args.lock_path,
        interface_version=args.interface_version,
    ).inject_requirements(
        component_requires_file=args.component_requires_file,
        component_list_file=_component_list_file(args.build_dir),
    )


def main():
    setup_logging()

    parser = argparse.ArgumentParser(
        description='Tool to be used by CMake build system to '
        'prepare components from package manager.'
    )

    parser.add_argument('--project_dir', help='Project directory')

    # Interface versions support:
    # *0* supports ESP-IDF <=4.4
    # *1* starting ESP-IDF 5.0
    # *2* starting ESP-IDF 5.1
    # *3* starting ESP-IDF 5.2
    # *4* starting ESP-IDF 5.5

    parser.add_argument(
        '--interface_version',
        help='Version of ESP-IDF build system integration',
        default=0,
        type=int,
        choices=[0, 1, 2, 3, 4],
    )

    parser.add_argument('--lock_path', help='lock file path relative to the project path')
    parser.add_argument(
        '--sdkconfig_json_file',
        required=False,
        help='Path to file with sdkconfig.json, used for parsing kconfig in if clauses',
    )
    subparsers = parser.add_subparsers(dest='step')
    subparsers.required = True

    prepare_step = subparsers.add_parser(
        'prepare_dependencies',
        help='Solve and download dependencies and provide directories to build system',
    )
    prepare_step.set_defaults(func=prepare_dep_dirs)
    prepare_step.add_argument(
        '--managed_components_list_file',
        help='Path to file with list of managed component directories (output)',
        required=True,
    )
    prepare_step.add_argument(
        '--local_components_list_file',
        help=(
            'Path to file with list of components discovered by build system (input). '
            'Only "components" directory will be processed if argument is not provided'
        ),
        required=False,
    )
    prepare_step.add_argument(
        '--build_dir',
        help='Working directory for build process',
        required=False,
    )

    inject_step_data = [
        {
            'name': 'inject_requirements',
        },
        {
            # Workaround for the typo in idf 4.1-4.2 (Remove after ESP-IDF 4.3 EOL)
            'name': 'inject_requrements',
            'extra_help': ' (alias)',
        },
    ]

    for step in inject_step_data:
        inject_step = subparsers.add_parser(
            step['name'], help=f'Inject requirements to CMake{step.get("extra_help", "")}'
        )
        inject_step.set_defaults(func=inject_requirements)
        inject_step.add_argument(
            '--component_requires_file',
            help='Path to temporary file with component requirements',
            required=True,
        )
        inject_step.add_argument(
            '--build_dir',
            help='Working directory for build process',
            required=True,
        )
        inject_step.add_argument('--idf_path', help='Path to IDF')

    args = parser.parse_args()

    try:
        args.func(args)
    except FatalError as e:
        error(str(e))
        sys.exit(e.exit_code)
