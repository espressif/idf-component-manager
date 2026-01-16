#!/usr/bin/env python
#
# SPDX-FileCopyrightText: 2019-2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
#
# 'prepare.py' is a tool to be used by CMake build system to prepare components
# from package manager

import argparse
import os
import shutil
import sys
import typing as t
from pathlib import Path

import psutil

from idf_component_manager.core import ComponentManager
from idf_component_tools import error, notice, setup_logging, warn
from idf_component_tools.build_system_tools import get_idf_version
from idf_component_tools.debugger import KCONFIG_CONTEXT
from idf_component_tools.errors import FatalError
from idf_component_tools.manifest import ComponentRequirement

CMAKEV2 = os.environ.get('IDF_BUILD_V2', 'n') == 'y'


def _component_list_file(build_dir):
    return os.path.join(build_dir, 'components_with_manifests_list.temp')


def get_cmake_pid():
    """
    Find the PID of the CMake process that initiated this build.

    This script is invoked multiple times during a single CMake build
    (prepare_dependencies, inject_requirements). On Linux and macOS,
    os.getppid() consistently returns the same parent PID across invocations.

    On Windows, however, each invocation of this script is spawned through a
    new intermediate process (e.g. cmd.exe), so os.getppid() returns a different
    PID each time. This causes multiple state files to be created instead of
    sharing one per CMake build, breaking the run counter and component list logic.

    This function walks up the process tree to find the CMake process itself,
    which remains constant throughout the build, ensuring consistent state file
    naming across all invocations.

    Returns:
        The PID of the CMake parent process, or os.getppid() as a fallback
        if no CMake process is found in the ancestry.
    """
    current = psutil.Process()
    while current.parent():
        parent = current.parent()
        if 'cmake' in parent.name().lower():
            return parent.pid
        current = parent
    return os.getppid()


class RunCounter:
    def __init__(self, build_dir: t.Union[str, Path]):
        self._file_path = Path(build_dir) / f'component_manager_run_counter.{get_cmake_pid()}'

        if not self._file_path.exists():
            self._file_path.write_text('0')

    @property
    def value(self) -> int:
        """
        Current value of the counter.
        """
        try:
            return int(self._file_path.read_text().strip())
        except (FileNotFoundError, ValueError):
            # Fallback if file was deleted externally or contains garbage
            return 0

    def increase(self) -> None:
        """
        Increments the counter by 1.
        """
        # Since __init__ guarantees creation, we can simply update logic.
        # We still catch FileNotFoundError in case it was deleted externally.
        if not self._file_path.exists():
            return

        self._file_path.write_text(str(self.value + 1))

    def cleanup(self) -> None:
        """
        Removes the counter file.
        """
        if self._file_path.exists():
            self._file_path.unlink()


def _get_ppid_file_path(local_component_list_file: t.Optional[str]) -> Path:
    return Path(f'{local_component_list_file}.{get_cmake_pid()}')


def _get_component_list_file(local_components_list_file):
    """
    Get the appropriate component list file, preferring the PPID version
    if it exists from a parent CMake run.

    Args:
        args: Command line arguments containing local_components_list_file

    Returns:
        Path to the component list file to use, or None if not configured
    """
    if not local_components_list_file:
        return None

    component_list_parent_pid = _get_ppid_file_path(local_components_list_file)
    # Always use local component list file from the first execution of the component manager
    # (component_list_parent_pid) during one CMake run,
    # to be sure that it doesn't contain components introduced by the component manager.
    if component_list_parent_pid.exists():
        return component_list_parent_pid
    else:
        return local_components_list_file


def _get_sdkconfig_json_file_path(args, build_dir) -> t.Optional[Path]:
    """
    Returns the path to the sdkconfig.json file if found, None otherwise.
    `sdkconfig_json_file` argument is not provided in some ESP-IDF versions (5.5.0, 5.5.1,...) when injecting deps
    so there's a fallback to the default known location.
    """
    if args.sdkconfig_json_file:
        return Path(args.sdkconfig_json_file)
    elif args.interface_version >= 4 and build_dir:
        return Path(build_dir) / 'config' / 'sdkconfig.json'

    return None


def prepare_dep_dirs(args):
    build_dir = args.build_dir or os.path.dirname(args.managed_components_list_file)

    # If the Component Manager has been run before, we need to update the Kconfig context with the sdkconfig.json file
    sdk_config_json_path = _get_sdkconfig_json_file_path(args, build_dir)
    # CMake V2 has valid sdkconfig.json right away
    if sdk_config_json_path and (RunCounter(build_dir).value > 0 or CMAKEV2):
        KCONFIG_CONTEXT.get().update_from_file(sdk_config_json_path)

    local_components_list_file = _get_component_list_file(args.local_components_list_file)

    ComponentManager(
        args.project_dir,
        lock_path=args.lock_path,
        interface_version=args.interface_version,
    ).prepare_dep_dirs(
        managed_components_list_file=args.managed_components_list_file,
        component_list_file=_component_list_file(build_dir),
        local_components_list_file=local_components_list_file,
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
        if args.interface_version < 4:
            notice(
                f'The following Kconfig variables were used in "if" clauses, '
                f'but not supported by your ESP-IDF version {get_idf_version()}. '
                f'Ignoring these if-clauses:\n'
                f'{_nl.join(sorted(debug_strs))}\n'
            )
            return

        warn(
            f'The following Kconfig variables were used in "if" clauses, '
            f'but not found in any Kconfig file:\n'
            f'{_nl.join(sorted(debug_strs))}\n'
        )

        # Copy local component list file for next run of CMake before exiting
        if args.local_components_list_file:
            ppid_file = _get_ppid_file_path(args.local_components_list_file)

            if not Path(ppid_file).exists():
                try:
                    shutil.copyfile(args.local_components_list_file, ppid_file)
                except (OSError, IOError) as e:
                    raise FatalError(
                        f"Failed to copy '{args.local_components_list_file}' → '{ppid_file}': {e}"
                    ) from e

        # Exiting with code 10 to signal CMake to re-run component discovery due to missing KConfig options
        sys.exit(10)

    # Clean up PPID file on successful completion
    if args.local_components_list_file:
        ppid_file_path = Path(_get_ppid_file_path(args.local_components_list_file))
        if ppid_file_path.exists():
            ppid_file_path.unlink()


def inject_requirements(args):
    sdk_config_json_path = _get_sdkconfig_json_file_path(args, args.build_dir)

    if sdk_config_json_path and (RunCounter(args.build_dir).value > 0 or CMAKEV2):
        KCONFIG_CONTEXT.get().update_from_file(sdk_config_json_path)

    ComponentManager(
        args.project_dir,
        lock_path=args.lock_path,
        interface_version=args.interface_version,
    ).inject_requirements(
        component_requires_file=args.component_requires_file,
        component_list_file=_component_list_file(args.build_dir),
        cm_run_counter=RunCounter(args.build_dir).value,
    )

    # Last run of prepare_dep_dirs was successful -> Clean up CM Run counter
    # If we're running CMakeV2, do not take counter into consideration
    if not CMAKEV2:
        if not Path(
            _get_ppid_file_path(f'{args.build_dir}/local_components_list.temp.yml')
        ).exists():
            RunCounter(args.build_dir).cleanup()
        else:
            RunCounter(args.build_dir).increase()


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
    # *4* starting ESP-IDF 6.0

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
