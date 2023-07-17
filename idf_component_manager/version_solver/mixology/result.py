# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2018 Sébastien Eustace
# SPDX-License-Identifier: MIT License
# SPDX-FileContributor: 2022-2023 Espressif Systems (Shanghai) CO LTD

try:
    from typing import Dict
except ImportError:
    pass

from idf_component_manager.version_solver.mixology.package import Package
from idf_component_tools.manifest import HashedComponentVersion


class SolverResult:
    def __init__(
        self, decisions, attempted_solutions
    ):  # type: (Dict[Package, HashedComponentVersion], int) -> None
        self._decisions = decisions
        self._attempted_solutions = attempted_solutions

    @property
    def decisions(self):  # type: () -> Dict[Package, HashedComponentVersion]
        return self._decisions

    @property
    def attempted_solutions(self):  # type: () -> int
        return self._attempted_solutions
