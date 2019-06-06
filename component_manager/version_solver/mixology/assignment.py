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

from typing import Any

from .incompatibility import Incompatibility
from .term import Term


class Assignment(Term):
    """
    A term in a PartialSolution that tracks some additional metadata.
    """

    def __init__(self, dependency, is_positive, decision_level, index, cause=None):
        super(Assignment, self).__init__(dependency, is_positive)

        self._decision_level = decision_level
        self._index = index
        self._cause = cause

    @property
    def decision_level(self):  # type: () -> int
        return self._decision_level

    @property
    def index(self):  # type: () -> int
        return self._index

    @property
    def cause(self):  # type: () -> Incompatibility
        return self._cause

    @classmethod
    def decision(cls, package, decision_level, index):  # type: (Any, int, int) -> Assignment
        return cls(package.to_dependency(), True, decision_level, index)

    @classmethod
    def derivation(cls, dependency, is_positive, cause, decision_level,
                   index):  # type: (Any, bool, Incompatibility, int, int) -> Assignment
        return cls(dependency, is_positive, decision_level, index, cause)

    def is_decision(self):  # type: () -> bool
        return self._cause is None
