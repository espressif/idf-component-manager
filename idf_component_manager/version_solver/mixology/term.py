# SPDX-FileCopyrightText: 2018 Sébastien Eustace
# SPDX-License-Identifier: MIT License
# SPDX-FileContributor: 2022-2024 Espressif Systems (Shanghai) CO LTD
from __future__ import annotations

import typing as t

from .constraint import Constraint
from .package import Package
from .set_relation import SetRelation


class Term:
    """
    A statement about a package which is true or false for a given selection of
    package versions.
    """

    def __init__(self, constraint: Constraint, is_positive: bool) -> None:
        self._constraint = constraint
        self._package = constraint.package
        self._positive = is_positive
        self._normalized_constraint = None
        self._empty = None

    @property
    def inverse(self) -> Term:
        return Term(self.constraint, not self.is_positive())

    @property
    def package(self) -> Package:
        return self._package

    @property
    def constraint(self) -> Constraint:
        return self._constraint

    @property
    def normalized_constraint(self) -> Constraint:
        if self._normalized_constraint is None:
            self._normalized_constraint = (
                self.constraint if self.is_positive() else self.constraint.inverse
            )

        return self._normalized_constraint

    def is_positive(self) -> bool:
        return self._positive

    def satisfies(self, other: Term) -> bool:
        """
        Returns whether this term satisfies another.
        """
        return self._package == other.package and self.relation(other) == SetRelation.SUBSET

    def relation(self, other: Term) -> SetRelation:
        """
        Returns the relationship between the package versions
        allowed by this term and another.
        """
        if self.package != other.package:
            raise ValueError(f'{other} should refer to {self.package}')

        if other.is_positive():
            if self.is_positive():
                if not self.is_compatible_with(other):
                    return SetRelation.DISJOINT

                # foo ^1.5.0 is a subset of foo ^1.0.0
                if other.constraint.allows_all(self.constraint):
                    return SetRelation.SUBSET

                # foo ^2.0.0 is disjoint with foo ^1.0.0
                if not self.constraint.allows_any(other.constraint):
                    return SetRelation.DISJOINT

                return SetRelation.OVERLAPPING
            else:
                if not self.is_compatible_with(other):
                    return SetRelation.OVERLAPPING

                # not foo ^1.0.0 is disjoint with foo ^1.5.0
                if self.constraint.allows_all(other.constraint):
                    return SetRelation.DISJOINT

                # not foo ^1.5.0 overlaps foo ^1.0.0
                # not foo ^2.0.0 is a superset of foo ^1.5.0
                return SetRelation.OVERLAPPING
        else:
            if self.is_positive():
                if not self.is_compatible_with(other):
                    return SetRelation.SUBSET

                # foo ^2.0.0 is a subset of not foo ^1.0.0
                if not other.constraint.allows_any(self.constraint):
                    return SetRelation.SUBSET

                # foo ^1.5.0 is disjoint with not foo ^1.0.0
                if other.constraint.allows_all(self.constraint):
                    return SetRelation.DISJOINT

                # foo ^1.0.0 overlaps not foo ^1.5.0
                return SetRelation.OVERLAPPING
            else:
                if not self.is_compatible_with(other):
                    return SetRelation.OVERLAPPING

                # not foo ^1.0.0 is a subset of not foo ^1.5.0
                if self.constraint.allows_all(other.constraint):
                    return SetRelation.SUBSET

                # not foo ^2.0.0 overlaps not foo ^1.0.0
                # not foo ^1.5.0 is a superset of not foo ^1.0.0
                return SetRelation.OVERLAPPING

    def intersect(self, other: Term) -> t.Optional[Term]:
        """
        Returns a Term that represents the packages
        allowed by both this term and another
        """
        if self.package != other.package:
            raise ValueError(f'{other} should refer to {self.package}')

        if self.is_compatible_with(other):
            if self.is_positive() != other.is_positive():
                # foo ^1.0.0 ∩ not foo ^1.5.0 → foo >=1.0.0 <1.5.0
                positive = self if self.is_positive() else other
                negative = other if self.is_positive() else self

                return self._non_empty_term(
                    positive.constraint.difference(negative.constraint), True
                )
            elif self.is_positive():
                # foo ^1.0.0 ∩ foo >=1.5.0 <3.0.0 → foo ^1.5.0
                return self._non_empty_term(self.constraint.intersect(other.constraint), True)
            else:
                # not foo ^1.0.0 ∩ not foo >=1.5.0 <3.0.0 → not foo >=1.0.0 <3.0.0
                return self._non_empty_term(self.constraint.union(other.constraint), False)
        elif self.is_positive() != other.is_positive():
            return self if self.is_positive() else other
        else:
            return

    def difference(self, other: Term) -> Term:
        """
        Returns a Term that represents packages
        allowed by this term and not by the other
        """
        return self.intersect(other.inverse)

    def is_compatible_with(self, other: Term) -> bool:
        return (
            self.package == Package.root()
            or other.package == Package.root()
            or self.package == other.package
        )

    def is_empty(self) -> bool:
        if self._empty is None:
            self._empty = self.normalized_constraint.is_empty()

        return self._empty

    def _non_empty_term(self, constraint: Constraint, is_positive: bool) -> t.Optional[Term]:
        if constraint.is_empty():
            return

        return Term(constraint, is_positive)

    def to_string(self, allow_every: bool = False) -> str:
        if self.is_positive():
            return self.constraint.to_string(allow_every=allow_every)

        return f'not {self.constraint}'

    def __str__(self):
        return self.to_string()

    def __repr__(self):
        return f'<Term {str(self)}>'
