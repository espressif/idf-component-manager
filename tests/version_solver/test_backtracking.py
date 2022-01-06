from idf_component_manager.version_solver.mixology.package import Package


def test_circular_dependency_on_older_version(source, check_solver_result):
    source.root_dep(Package('a'), '>=1.0.0')

    source.add(Package('a'), '1.0.0')
    source.add(Package('a'), '2.0.0', deps={Package('b'): '1.0.0'})
    source.add(Package('b'), '1.0.0', deps={Package('a'): '1.0.0'})

    check_solver_result(source, {Package('a'): '1.0.0'}, tries=2)


def test_diamond_dependency_graph(source, check_solver_result):
    source.root_dep(Package('a'), '*')
    source.root_dep(Package('b'), '*')

    source.add(Package('a'), '2.0.0', deps={Package('c'): '^1.0.0'})
    source.add(Package('a'), '1.0.0')

    source.add(Package('b'), '2.0.0', deps={Package('c'): '^3.0.0'})
    source.add(Package('b'), '1.0.0', deps={Package('c'): '^2.0.0'})

    source.add(Package('c'), '3.0.0')
    source.add(Package('c'), '2.0.0')
    source.add(Package('c'), '1.0.0')

    check_solver_result(source, {Package('a'): '1.0.0', Package('b'): '2.0.0', Package('c'): '3.0.0'})


def test_backjumps_after_partial_satisfier(source, check_solver_result):
    # c 2.0.0 is incompatible with y 2.0.0 because it requires x 1.0.0, but that
    # requirement only exists because of both a and b. The solver should be able
    # to deduce c 2.0.0's incompatibility and select c 1.0.0 instead.
    source.root_dep(Package('c'), '*')
    source.root_dep(Package('y'), '^2.0.0')

    source.add(Package('a'), '1.0.0', deps={Package('x'): '>=1.0.0'})
    source.add(Package('b'), '1.0.0', deps={Package('x'): '<2.0.0'})

    source.add(Package('c'), '1.0.0')
    source.add(Package('c'), '2.0.0', deps={Package('a'): '*', Package('b'): '*'})

    source.add(Package('x'), '0.0.0')
    source.add(Package('x'), '1.0.0', deps={Package('y'): '1.0.0'})
    source.add(Package('x'), '2.0.0')

    source.add(Package('y'), '1.0.0')
    source.add(Package('y'), '2.0.0')

    check_solver_result(source, {Package('c'): '1.0.0', Package('y'): '2.0.0'}, tries=2)


def test_rolls_back_leaf_versions_first(source, check_solver_result):
    # The latest versions of a and b disagree on c. An older version of either
    # will resolve the problem. This test validates that b, which is farther
    # in the dependency graph from myapp is downgraded first.
    source.root_dep(Package('a'), '*')

    source.add(Package('a'), '1.0.0', deps={Package('b'): '*'})
    source.add(Package('a'), '2.0.0', deps={Package('b'): '*', Package('c'): '2.0.0'})
    source.add(Package('b'), '1.0.0')
    source.add(Package('b'), '2.0.0', deps={Package('c'): '1.0.0'})
    source.add(Package('c'), '1.0.0')
    source.add(Package('c'), '2.0.0')

    check_solver_result(source, {Package('a'): '2.0.0', Package('b'): '1.0.0', Package('c'): '2.0.0'})


def test_simple_transitive(source, check_solver_result):
    # Only one version of baz, so foo and bar will have to downgrade
    # until they reach it
    source.root_dep(Package('foo'), '*')

    source.add(Package('foo'), '1.0.0', deps={Package('bar'): '1.0.0'})
    source.add(Package('foo'), '2.0.0', deps={Package('bar'): '2.0.0'})
    source.add(Package('foo'), '3.0.0', deps={Package('bar'): '3.0.0'})

    source.add(Package('bar'), '1.0.0', deps={Package('baz'): '*'})
    source.add(Package('bar'), '2.0.0', deps={Package('baz'): '2.0.0'})
    source.add(Package('bar'), '3.0.0', deps={Package('baz'): '3.0.0'})

    source.add(Package('baz'), '1.0.0')

    check_solver_result(source, {Package('foo'): '1.0.0', Package('bar'): '1.0.0', Package('baz'): '1.0.0'}, tries=3)


def test_backjump_to_nearer_unsatisfied_package(source, check_solver_result):
    # This ensures it doesn't exhaustively search all versions of b when it's
    # a-2.0.0 whose dependency on c-2.0.0-nonexistent led to the problem. We
    # make sure b has more versions than a so that the solver tries a first
    # since it sorts sibling dependencies by number of versions.
    source.root_dep(Package('a'), '*')
    source.root_dep(Package('b'), '*')

    source.add(Package('a'), '1.0.0', deps={Package('c'): '1.0.0'})
    source.add(Package('a'), '2.0.0', deps={Package('c'): '2.0.0-nonexistent'})
    source.add(Package('b'), '1.0.0')
    source.add(Package('b'), '2.0.0')
    source.add(Package('b'), '3.0.0')
    source.add(Package('c'), '1.0.0')

    check_solver_result(source, {Package('a'): '1.0.0', Package('b'): '3.0.0', Package('c'): '1.0.0'}, tries=2)


def test_traverse_into_package_with_fewer_versions_first(source, check_solver_result):
    # Dependencies are ordered so that packages with fewer versions are tried
    # first. Here, there are two valid solutions (either a or b must be
    # downgraded once). The chosen one depends on which dep is traversed first.
    # Since b has fewer versions, it will be traversed first, which means a will
    # come later. Since later selections are revised first, a gets downgraded.
    source.root_dep(Package('a'), '*')
    source.root_dep(Package('b'), '*')

    source.add(Package('a'), '1.0.0', deps={Package('c'): '*'})
    source.add(Package('a'), '2.0.0', deps={Package('c'): '*'})
    source.add(Package('a'), '3.0.0', deps={Package('c'): '*'})
    source.add(Package('a'), '4.0.0', deps={Package('c'): '*'})
    source.add(Package('a'), '5.0.0', deps={Package('c'): '1.0.0'})
    source.add(Package('b'), '1.0.0', deps={Package('c'): '*'})
    source.add(Package('b'), '2.0.0', deps={Package('c'): '*'})
    source.add(Package('b'), '3.0.0', deps={Package('c'): '*'})
    source.add(Package('b'), '4.0.0', deps={Package('c'): '2.0.0'})
    source.add(Package('c'), '1.0.0')
    source.add(Package('c'), '2.0.0')

    check_solver_result(source, {Package('a'): '4.0.0', Package('b'): '4.0.0', Package('c'): '2.0.0'})


def test_backjump_past_failed_package_on_disjoint_constraint(source, check_solver_result):
    source.root_dep(Package('a'), '*')
    source.root_dep(Package('foo'), '>2.0.0')

    source.add(Package('a'), '1.0.0', deps={Package('foo'): '*'})  # ok
    source.add(Package('a'), '2.0.0', deps={Package('foo'): '<1.0.0'})  # disjoint with myapp's constraint on foo

    source.add(Package('foo'), '2.0.0')
    source.add(Package('foo'), '2.0.1')
    source.add(Package('foo'), '2.0.2')
    source.add(Package('foo'), '2.0.3')
    source.add(Package('foo'), '2.0.4')

    check_solver_result(source, {Package('a'): '1.0.0', Package('foo'): '2.0.4'})
