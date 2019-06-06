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


class SolverResult:
    def __init__(self, root, packages, attempted_solutions):
        self._root = root
        self._packages = packages
        self._attempted_solutions = attempted_solutions

    @property
    def packages(self):
        return self._packages

    @property
    def attempted_solutions(self):
        return self._attempted_solutions
