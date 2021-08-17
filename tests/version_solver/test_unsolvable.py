from idf_component_manager.version_solver.mixology.package import Package

from .helpers import check_solver_result


def test_no_version_matching_constraint(source):
    source.root_dep(Package('foo'), '^1.0')

    source.add(Package('foo'), '2.0.0')
    source.add(Package('foo'), '2.1.3')

    check_solver_result(
        source,
        error=('Because root depends on foo (^1.0) '
               "which doesn't match any versions, version solving failed."),
    )


def test_no_version_that_matches_combined_constraints(source):
    source.root_dep(Package('foo'), '1.0.0')
    source.root_dep(Package('bar'), '1.0.0')

    source.add(Package('foo'), '1.0.0', deps={Package('shared'): '>=2.0.0,<3.0.0'})
    source.add(Package('bar'), '1.0.0', deps={Package('shared'): '>=2.9.0,<4.0.0'})
    source.add(Package('shared'), '2.5.0')
    source.add(Package('shared'), '3.5.0')

    error = """\
Because foo (1.0.0) depends on shared (>=2.0.0,<3.0.0)
 and no versions of shared match >=2.9.0,<3.0.0, foo (1.0.0) requires shared (>=2.0.0,<2.9.0).
And because bar (1.0.0) depends on shared (>=2.9.0,<4.0.0), bar (1.0.0) is incompatible with foo (1.0.0).
So, because root depends on both foo (1.0.0) and bar (1.0.0), version solving failed."""

    check_solver_result(source, error=error)


def test_disjoint_constraints(source):
    source.root_dep(Package('foo'), '1.0.0')
    source.root_dep(Package('bar'), '1.0.0')

    source.add(Package('foo'), '1.0.0', deps={Package('shared'): '<=2.0.0'})
    source.add(Package('bar'), '1.0.0', deps={Package('shared'): '>3.0.0'})
    source.add(Package('shared'), '2.0.0')
    source.add(Package('shared'), '4.0.0')

    error = """\
Because bar (1.0.0) depends on shared (>3.0.0)
 and foo (1.0.0) depends on shared (<=2.0.0), bar (1.0.0) is incompatible with foo (1.0.0).
So, because root depends on both foo (1.0.0) and bar (1.0.0), version solving failed."""

    check_solver_result(source, error=error)


def test_disjoint_root_constraints(source):
    source.root_dep(Package('foo'), '1.0.0')
    source.root_dep(Package('foo'), '2.0.0')

    source.add(Package('foo'), '1.0.0')
    source.add(Package('foo'), '2.0.0')

    error = """\
Because root depends on both foo (1.0.0) and foo (2.0.0), version solving failed."""

    check_solver_result(source, error=error)


def test_no_valid_solution(source):
    source.root_dep(Package('a'), '*')
    source.root_dep(Package('b'), '*')

    source.add(Package('a'), '1.0.0', deps={Package('b'): '1.0.0'})
    source.add(Package('a'), '2.0.0', deps={Package('b'): '2.0.0'})

    source.add(Package('b'), '1.0.0', deps={Package('a'): '2.0.0'})
    source.add(Package('b'), '2.0.0', deps={Package('a'): '1.0.0'})

    error = """\
Because no versions of b match >=0.0.0,<1.0.0 || >1.0.0,<2.0.0 || >2.0.0
 and b (1.0.0) depends on a (2.0.0), b (>=0.0.0,<2.0.0 || >2.0.0) requires a (2.0.0).
And because a (2.0.0) depends on b (2.0.0), b is forbidden.
Because b (2.0.0) depends on a (1.0.0) which depends on b (1.0.0), b is forbidden.
Thus, b is forbidden.
So, because root depends on b (*), version solving failed."""

    check_solver_result(source, error=error, tries=2)
