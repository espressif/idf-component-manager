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


def main(args):
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Tool to be used by CMake build system to prepare components from package manager.')
    parser.add_argument('--cmake_command', help='Path to CMake command')
    parser.add_argument('--idf_path', help='Path to IDF')
    parser.add_argument('--build_dir', help='Working directory for build process')
    parser.add_argument('--build_properties_file', help='Path to temporary file with build properties')
    parser.add_argument('--component_properties_file', help='Path to temporary file with component properties')
    parser.add_argument('--component_requires_file', help='Path to temporary file with component requirements')
    args = parser.parse_args()
    main(args)
