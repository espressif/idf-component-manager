# SPDX-FileCopyrightText: 2018 Sébastien Eustace
# SPDX-License-Identifier: MIT License
# SPDX-FileContributor: 2022-2024 Espressif Systems (Shanghai) CO LTD

import typing as t

from idf_component_manager.version_solver.mixology.package import Package
from idf_component_tools.utils import HashedComponentVersion


class SolverResult:
    def __init__(
        self, decisions: t.Dict[Package, HashedComponentVersion], attempted_solutions: int
    ) -> None:
        self._decisions = decisions
        self._attempted_solutions = attempted_solutions

    @property
    def decisions(self) -> t.Dict[Package, HashedComponentVersion]:
        return self._decisions

    @property
    def attempted_solutions(self) -> int:
        return self._attempted_solutions
