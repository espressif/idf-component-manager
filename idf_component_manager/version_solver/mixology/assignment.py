# SPDX-FileCopyrightText: 2018 Sébastien Eustace
# SPDX-License-Identifier: MIT License
# SPDX-FileContributor: 2022-2024 Espressif Systems (Shanghai) CO LTD

from __future__ import annotations

import typing as t

from .constraint import Constraint
from .incompatibility import Incompatibility
from .package import Package
from .range import Range
from .term import Term


class Assignment(Term):
    """
    A term in a PartialSolution that tracks some additional metadata.
    """

    def __init__(
        self,
        constraint: Constraint,
        is_positive: bool,
        decision_level: int,
        index: int,
        cause: t.Optional[Incompatibility] = None,
    ) -> None:
        super().__init__(constraint, is_positive)

        self._decision_level = decision_level
        self._index = index
        self._cause = cause

    @property
    def decision_level(self) -> int:
        return self._decision_level

    @property
    def index(self) -> int:
        return self._index

    @property
    def cause(self) -> Incompatibility:
        return self._cause

    @classmethod
    def decision(
        cls, package: Package, version: t.Any, decision_level: int, index: int
    ) -> Assignment:
        return cls(
            Constraint(package, Range(version, version, True, True)),
            True,
            decision_level,
            index,
        )

    @classmethod
    def derivation(
        cls,
        constraint: Constraint,
        is_positive: bool,
        cause: Incompatibility,
        decision_level: int,
        index: int,
    ) -> Assignment:
        return cls(constraint, is_positive, decision_level, index, cause)

    def is_decision(self) -> bool:
        return self._cause is None
