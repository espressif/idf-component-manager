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
# Contains code taken from "poetry" python package
# https://github.com/sdispater/poetry
# Copyright (c) 2018 Sébastien Eustace
# Originally released under MIT license

from .version_solver import VersionSolver


def resolve_version(root, provider, locked=None, use_latest=None):
    solver = VersionSolver(root, provider, locked=locked, use_latest=use_latest)

    return solver.solve()