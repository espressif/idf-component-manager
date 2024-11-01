# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import typing as t

from idf_component_tools import debug
from idf_component_tools.semver import Range as SemverRange
from idf_component_tools.semver import SimpleSpec
from idf_component_tools.utils import HashedComponentVersion

from .mixology.constraint import Constraint
from .mixology.failure import SolverFailure
from .mixology.package import Package
from .mixology.package_source import PackageSource as BasePackageSource
from .mixology.range import Range
from .mixology.union import Union


def parse_constraint(spec: str) -> t.Union[Union, Range]:
    try:
        clause = SimpleSpec(spec).clause
    except ValueError:  # if not semspec, expect an exact version
        constraint = parse_single_constraint(HashedComponentVersion(spec))
    else:
        if isinstance(clause, SemverRange):  # single range
            constraint = parse_single_constraint(clause)
        else:  # multi ranges
            ranges = [parse_single_constraint(_range) for _range in clause.clauses]
            constraint = ranges[0]
            for r in ranges[1:]:
                constraint = constraint.intersect(r)

    return constraint


def parse_single_constraint(
    _range: t.Union[SemverRange, HashedComponentVersion],
) -> t.Union[Union, Range]:
    if isinstance(_range, HashedComponentVersion):  # not semver
        return Range(_range, _range, True, True, _range.text)

    version = HashedComponentVersion(str(_range.target))
    if _range.operator == _range.OP_LT:
        return Range(max=version, string=str(_range))
    elif _range.operator == _range.OP_LTE:
        return Range(max=version, include_max=True, string=str(_range))
    elif _range.operator == _range.OP_GT:
        return Range(min=version, string=str(_range))
    elif _range.operator == _range.OP_GTE:
        return Range(min=version, include_min=True, string=str(_range))
    elif _range.operator == _range.OP_NEQ:
        return Union(Range(max=version, string=str(_range)), Range(min=version, string=str(_range)))
    else:
        return Range(version, version, True, True, str(_range))


def parse_root_dep_conflict_constraints(failure: SolverFailure) -> t.List[Constraint]:
    terms = failure._incompatibility.terms
    res = []
    if len(terms) == 1 and terms[0].package == Package.root():  # root dep
        conflict_terms = failure._incompatibility.cause.conflict.terms
        for conflict_term in conflict_terms:
            res.append(conflict_term.constraint)

    return res


class Dependency:
    def __init__(self, package: Package, spec: str) -> None:
        self.package = package
        self.constraint = parse_constraint(spec)
        self.text = spec


class PackageSource(BasePackageSource):
    def __init__(self) -> None:
        self._root_version = HashedComponentVersion('0.0.0')
        self._root_dependencies: t.List[Dependency] = []
        self._packages: t.Dict[Package, t.Dict[HashedComponentVersion, t.List[Dependency]]] = {}

        super().__init__()

    @property
    def root_version(self):
        return self._root_version

    def add(
        self,
        package: Package,
        version: t.Union[str, HashedComponentVersion],
        deps: t.Optional[t.Dict[Package, str]] = None,
    ):
        if deps is None:
            deps = {}

        if not isinstance(version, HashedComponentVersion):
            version = HashedComponentVersion(version)

        if package not in self._packages:
            self._packages[package] = {}

        if version in self._packages[package]:
            return

        dependencies = []
        for dep_package, spec in deps.items():
            if dep_package.source:
                spec = dep_package.source.normalize_spec(spec)

            dependencies.append(Dependency(dep_package, spec))

        self._packages[package][version] = dependencies

    def override_dependencies(self, overriders: t.Set[str]) -> None:
        for package in list(self._packages.keys()):
            if not package.source.is_overrider and package.name in overriders:
                del self._packages[package]

        for package in self._packages.keys():
            for version in self._packages[package].keys():
                self._packages[package][version] = [
                    elem
                    for elem in self._packages[package][version]
                    if elem.package.source.is_overrider or elem.package.name not in overriders
                ]

    def root_dep(self, package: Package, spec: str) -> None:
        if package.source:
            spec = package.source.normalize_spec(spec)

        debug(f'Adding root dependency: {repr(package)} {spec}')
        self._root_dependencies.append(Dependency(package, spec))

    def _versions_for(
        self, package: Package, constraint: t.Any = None
    ) -> t.List[HashedComponentVersion]:
        if package not in self._packages:
            return []

        versions = []
        for version in self._packages[package].keys():
            if not constraint or constraint.allows_any(Range(version, version, True, True)):
                versions.append(version)

        return sorted(versions, reverse=True)

    def dependencies_for(self, package: Package, version: t.Any) -> t.List[t.Any]:
        if package == self.root:
            return self._root_dependencies

        return self._packages[package][version]

    def convert_dependency(self, dependency: Dependency) -> Constraint:
        if isinstance(dependency.constraint, Range):
            constraint = Range(
                dependency.constraint.min,
                dependency.constraint.max,
                dependency.constraint.include_min,
                dependency.constraint.include_max,
                dependency.text,
            )
        elif isinstance(dependency.constraint, Union):
            ranges = [
                Range(
                    r.min,
                    r.max,
                    r.include_min,
                    r.include_max,
                    str(r),
                )
                for r in dependency.constraint.ranges
            ]
            constraint = Union.of(*ranges)
        else:
            raise ValueError('should be "Union" or "Range"')

        return Constraint(dependency.package, constraint)
