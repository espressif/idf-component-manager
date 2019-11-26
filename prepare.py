#!/usr/bin/env python
# coding=utf-8
#
# 'components/prepare.py' is a tool to be used by CMake build system to prepare components
# from package manager
#
#
# Copyright 2019 Espressif Systems (Shanghai) CO LTD
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

# WARNING: we don't check for Python build-time dependencies until
# check_environment() function below. If possible, avoid importing
# any external libraries here - put in external script, or import in
# their specific function instead.

import argparse
import subprocess  # nosec
import sys
import os
import re

from component_manager.core import ComponentManager


def _parse_build_properties(path):
    """
    Parse the CMake files of format:
    set(KEY value)

    Returns a dict of name:value.
    """
    result = {}
    with open(path) as f:
        for line in f:
            m = re.match(r"^set\(([\w]+)\s(.*)\)\n?", line)
            if m:
                result[m.group(1)] = m.group(2)
    return result


def prepare_dep_dirs(args):
    print('Running component manager')
    print(args)
    manager = ComponentManager(args.project_dir)
    manager.install()

    # TODO: deal with IDF as component-bundle

    # if solution.solved_components:
    #     with open(args.managed_components_list_file, 'w') as f:
    #         for component in solution.solved_components:
    #             print(component)
    #             f.write(component.name)


def inject_requrements(args):
    print('Injecting managed components requirements')
    # manager = ComponentManager(args.project_dir)
    # TODO: only load lock here
    # solution = manager.install()

    # if solution.solved_components:
    #     # Add components provided by package manager to component_properties_file
    #     with open(args.component_properties_file, 'r') as f:
    #         data = f.read()

    #     components_list = []

    #     with open(args.component_properties_file, 'w') as f:
    #         for component in solution.solved_components:
    #             if component.name == 'idf':
    #                 continue

    #             name_parts = component.name.split('/')

    #             if name_parts[0] == 'idf':
    #                 under_name = '_'.join(name_parts[1:])
    #                 semi_name = '::'.join(name_parts[1:])
    #             else:
    #                 under_name = '_'.join(name_parts)
    #                 semi_name = '::'.join(name_parts)

    #             components_list.append("___idf_%s;" % under_name)

    #             props = [
    #                 "\nset(__component____idf_%s_COMPONENT_LIB __idf_%s)" % (under_name, under_name),
    #                 (
    #                     "\nset(__component____idf_%s___COMPONENT_PROPERTIES "
    #                     "COMPONENT_LIB;__COMPONENT_PROPERTIES;COMPONENT_NAME;COMPONENT_DIR;COMPONENT_ALIAS;"
    #                     "__PREFIX;KCONFIG;KCONFIG_PROJBUILD;SDKCONFIG_RENAME)") % under_name,
    #                 "\nset(__component____idf_%s_COMPONENT_NAME %s)" % (under_name, semi_name),
    #                 "\nset(__component____idf_%s_COMPONENT_DIR %s)" %
    #                 (under_name, os.path.join(args.project_dir, "managed_components", *name_parts)),
    #                 "\nset(__component____idf_%s_COMPONENT_ALIAS idf::%s)" % (under_name, semi_name),
    #                 "\nset(__component____idf_%s___PREFIX idf)" % under_name,
    #                 # TODO: fill KCONFIG and KCONFIG_PROJBUILD values
    #                 "\nset(__component____idf_%s_KCONFIG)" % under_name,
    #                 "\nset(__component____idf_%s_KCONFIG_PROJBUILD)" % under_name,
    #                 "\nset(__component____idf_%s_SDKCONFIG_RENAME)" % under_name
    #             ]
    #             f.writelines(props)

    #         f.write(data)

    #     # Add components to build_properties.temp __COMPONENT_TARGETS
    #     build_props = _parse_build_properties(args.build_properties_file)
    #     build_props["__COMPONENT_TARGETS"] = ''.join(components_list) + build_props.get("__COMPONENT_TARGETS")
    #     with open(args.build_properties_file, 'w') as f:
    #         for key, value in build_props.items():
    #             f.write("\nset(%s %s)" % (key, value))

    # Run CMake script to aggregate dependencies
    subprocess.check_call(  # nosec
        [
            args.cmake_command, '-D', 'ESP_PLATFORM=1', '-D',
            'BUILD_PROPERTIES_FILE=%s' % args.build_properties_file, '-D',
            'COMPONENT_PROPERTIES_FILE=%s' % args.component_properties_file, '-D',
            'COMPONENT_REQUIRES_FILE=%s' % args.component_requires_file, '-P',
            os.path.join(args.idf_path, 'tools', 'cmake', 'scripts', 'component_get_requirements.cmake')
        ],
        stdout=sys.stdout,
        stderr=sys.stderr)

    # And update temporary requirements file
    # if solution.solved_components:
    #     with open(args.component_requires_file, 'r') as f:
    #         data = f.read()

    #     with open(args.component_requires_file, 'w') as f:
    #         for component in solution.solved_components:
    #             # TODO: deal with IDF as component-bundle
    #             if component.name == 'idf':
    #                 continue

    #             name_parts = component.name.split('/')
    #             f.write(
    #                 '\nidf_build_component("%s")' % os.path.join(args.project_dir, "managed_components", *name_parts))

    #         f.write(data)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Tool to be used by CMake build system to prepare components from package manager.')

    parser.add_argument('--project_dir', help='Project directory')

    subparsers = parser.add_subparsers(dest='step')
    subparsers.required = True

    prepare_step = subparsers.add_parser(
        'prepare_dep_dirs', help='Solve and download dependencies and provide directories to build system')
    prepare_step.set_defaults(func=prepare_dep_dirs)
    prepare_step.add_argument(
        '--managed_components_list_file', help='Path to file with list of managed component directories')

    inject_step = subparsers.add_parser('inject_requrements', help='Inject requirements to CMake')
    inject_step.set_defaults(func=inject_requrements)
    inject_step.add_argument('--build_properties_file', help='Path to temporary file with build properties')
    inject_step.add_argument('--component_properties_file', help='Path to temporary file with component properties')
    inject_step.add_argument('--component_requires_file', help='Path to temporary file with component requirements')
    inject_step.add_argument('--build_dir', help='Working directory for build process')
    inject_step.add_argument('--cmake_command', help='Path to CMake command')
    inject_step.add_argument('--idf_path', help='Path to IDF')

    args = parser.parse_args()
    args.func(args)
