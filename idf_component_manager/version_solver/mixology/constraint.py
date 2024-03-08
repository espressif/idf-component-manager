# SPDX-FileCopyrightText: 2018 Sébastien Eustace
# SPDX-License-Identifier: MIT License
# SPDX-FileContributor: 2022-2024 Espressif Systems (Shanghai) CO LTD
from __future__ import annotations

import typing as t

from .package import Package
from .range import Range
from .set_relation import SetRelation
from .union import Union


class Constraint:
    """
    A term constraint.
    """

    def __init__(self, package: Package, constraint: t.Union[Range, Union]) -> None:
        self._package = package
        self._constraint = constraint

    @property
    def package(self) -> Package:
        return self._package

    @property
    def constraint(self) -> t.Union[Range, Union]:
        return self._constraint

    @property
    def inverse(self) -> Constraint:
        new_constraint = self.constraint.inverse

        return self.__class__(self.package, new_constraint)

    def allows_all(self, other: Constraint) -> bool:
        return self.constraint.allows_all(other.constraint)

    def allows_any(self, other: Constraint) -> bool:
        return self.constraint.allows_any(other.constraint)

    def difference(self, other: Constraint) -> bool:
        if not isinstance(self.package.source, type(other.package.source)):
            raise ValueError('Cannot tell difference of two different source types')

        return self.__class__(self.package, self.constraint.difference(other.constraint))

    def intersect(self, other: Constraint) -> Constraint:
        if other.package != self.package:
            raise ValueError('Cannot intersect two constraints for different packages')

        if not isinstance(self.package.source, type(other.package.source)):
            raise ValueError('Cannot intersect two different source types')

        return self.__class__(self.package, self.constraint.intersect(other.constraint))

    def union(self, other: Constraint) -> Constraint:
        if other.package != self.package:
            raise ValueError('Cannot build an union of two constraints for different packages')

        if not isinstance(self.package.source, type(other.package.source)):
            raise ValueError('Cannot build an union of two different source types')

        return self.__class__(self.package, self.constraint.union(other.constraint))

    def is_subset_of(self, other: Constraint) -> bool:
        return other.allows_all(self)

    def overlaps(self, other: Constraint) -> bool:
        return other.allows_any(self)

    def is_disjoint_from(self, other: Constraint) -> bool:
        return not self.overlaps(other)

    def relation(self, other: Constraint) -> SetRelation:
        if self.is_subset_of(other):
            return SetRelation.SUBSET
        elif self.overlaps(other):
            return SetRelation.OVERLAPPING
        else:
            return SetRelation.DISJOINT

    def is_any(self) -> bool:
        return self._constraint.is_any()

    def is_empty(self) -> bool:
        return self._constraint.is_empty()

    def __eq__(self, other: Constraint) -> bool:
        if not isinstance(other, Constraint):
            return NotImplemented

        return other.package == self.package and other.constraint == self.constraint

    def __hash__(self):
        return hash(self.package) ^ hash(self.constraint)

    def to_string(self, allow_every: bool = False) -> str:
        if self.package == Package.root():
            return 'project'
        elif allow_every and self.is_any():
            return f'every version of {self.package}'

        return '{} ({})'.format(self.package, '*' if self.is_any() else str(self.constraint))

    def __str__(self):
        return self.to_string()
