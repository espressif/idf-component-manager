# SPDX-FileCopyrightText: 2018 Sébastien Eustace
# SPDX-License-Identifier: MIT License
# SPDX-FileContributor: 2022-2024 Espressif Systems (Shanghai) CO LTD

import typing as t
from collections import OrderedDict

from idf_component_tools.utils import HashedComponentVersion

from .assignment import Assignment
from .constraint import Constraint
from .incompatibility import Incompatibility
from .package import Package
from .set_relation import SetRelation
from .term import Term


class PartialSolution:
    """
    # A list of Assignments that represent the solver's current best guess about
    # what's true for the eventual set of package versions that will comprise the
    # total solution.
    #
    # See https://github.com/dart-lang/mixology/tree/master/doc/solver.md#partial-solution.
    """

    def __init__(self) -> None:
        # The assignments that have been made so far, in the order they were
        # assigned.
        self._assignments: t.List[Assignment] = []

        # The decisions made for each package.
        self._decisions: t.Dict[Package, HashedComponentVersion] = OrderedDict()

        # The intersection of all positive Assignments for each package, minus any
        # negative Assignments that refer to that package.
        #
        # This is derived from self._assignments.
        self._positive: t.Dict[Package, Term] = OrderedDict()

        # The union of all negative Assignments for each package.
        #
        # If a package has any positive Assignments, it doesn't appear in this
        # map.
        #
        # This is derived from self._assignments.
        self._negative: t.Dict[Package, t.Dict[Package, Term]] = OrderedDict()

        # The number of distinct solutions that have been attempted so far.
        self._attempted_solutions = 1

        # Whether the solver is currently backtracking.
        self._backtracking = False

    @property
    def decisions(self) -> t.Dict[Package, HashedComponentVersion]:
        return self._decisions

    @property
    def decision_level(self) -> int:
        return len(self._decisions)

    @property
    def attempted_solutions(self) -> int:
        return self._attempted_solutions

    @property
    def unsatisfied(self) -> t.List[Term]:
        return [term for term in self._positive.values() if term.package not in self._decisions]

    def decide(self, package: Package, version: HashedComponentVersion) -> None:
        """
        Adds an assignment of package as a decision
        and increments the decision level.
        """
        # When we make a new decision after backtracking, count an additional
        # attempted solution. If we backtrack multiple times in a row, though, we
        # only want to count one, since we haven't actually started attempting a
        # new solution.
        if self._backtracking:
            self._attempted_solutions += 1

        self._backtracking = False
        self._decisions[package] = version

        self._assign(
            Assignment.decision(package, version, self.decision_level, len(self._assignments))
        )

    def derive(self, constraint: Constraint, is_positive: bool, cause: Incompatibility) -> None:
        """
        Adds an assignment of package as a derivation.
        """
        self._assign(
            Assignment.derivation(
                constraint,
                is_positive,
                cause,
                self.decision_level,
                len(self._assignments),
            )
        )

    def _assign(self, assignment: Assignment) -> None:
        """
        Adds an Assignment to _assignments and _positive or _negative.
        """
        self._assignments.append(assignment)
        self._register(assignment)

    def backtrack(self, decision_level: int) -> None:
        """
        Resets the current decision level to decision_level, and removes all
        assignments made after that level.
        """
        self._backtracking = True

        packages = set()
        while self._assignments[-1].decision_level > decision_level:
            removed = self._assignments.pop(-1)
            packages.add(removed.package)
            if removed.is_decision():
                del self._decisions[removed.package]

        # Re-compute _positive and _negative for the packages that were removed.
        for package in packages:
            if package in self._positive:
                del self._positive[package]

            if package in self._negative:
                del self._negative[package]

        for assignment in self._assignments:
            if assignment.package in packages:
                self._register(assignment)

    def _register(self, assignment: Assignment) -> None:
        """
        Registers an Assignment in _positive or _negative.
        """
        package = assignment.package
        old_positive = self._positive.get(package)
        if old_positive is not None:
            self._positive[package] = old_positive.intersect(assignment)

            return

        ref = assignment.package
        negative_by_ref = self._negative.get(package)
        old_negative = None if negative_by_ref is None else negative_by_ref.get(ref)
        if old_negative is None:
            term = assignment
        else:
            term = assignment.intersect(old_negative)

        if term.is_positive():
            if package in self._negative:
                del self._negative[package]

            self._positive[package] = term
        else:
            if package not in self._negative:
                self._negative[package] = {}

            self._negative[package][package] = term

    def satisfier(self, term: Term) -> Assignment:
        """
        Returns the first Assignment in this solution such that the sublist of
        assignments up to and including that entry collectively satisfies term.
        """
        assigned_term: Term = None

        for assignment in self._assignments:
            if assignment.package != term.package:
                continue

            if assignment.package != Package.root() and not assignment.package == term.package:
                if not assignment.is_positive():
                    continue

                assert not term.is_positive()

                return assignment

            if assigned_term is None:
                assigned_term = assignment
            else:
                assigned_term = assigned_term.intersect(assignment)

            # As soon as we have enough assignments to satisfy term, return them.
            if assigned_term.satisfies(term):
                return assignment

        raise RuntimeError(f'[BUG] {term} is not satisfied.')

    def satisfies(self, term: Term) -> bool:
        return self.relation(term) == SetRelation.SUBSET

    def relation(self, term: Term) -> SetRelation:
        positive = self._positive.get(term.package)
        if positive is not None:
            return positive.relation(term)

        by_ref = self._negative.get(term.package)
        if by_ref is None:
            return SetRelation.OVERLAPPING

        negative = by_ref[term.package]
        if negative is None:
            return SetRelation.OVERLAPPING

        return negative.relation(term)
