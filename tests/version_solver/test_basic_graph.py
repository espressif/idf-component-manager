# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
from idf_component_manager.version_solver.mixology.package import Package
from idf_component_tools.sources import LocalSource, WebServiceSource


def test_simple_dependencies(source, check_solver_result):
    source.root_dep(Package('a'), '1.0.0')
    source.root_dep(Package('b'), '1.0.0')

    source.add(Package('a'), '1.0.0', deps={Package('aa'): '1.0.0', Package('ab'): '1.0.0'})
    source.add(Package('b'), '1.0.0', deps={Package('ba'): '1.0.0', Package('bb'): '1.0.0'})
    source.add(Package('aa'), '1.0.0')
    source.add(Package('ab'), '1.0.0')
    source.add(Package('ba'), '1.0.0')
    source.add(Package('bb'), '1.0.0')

    check_solver_result(
        source,
        {
            Package('a'): '1.0.0',
            Package('aa'): '1.0.0',
            Package('ab'): '1.0.0',
            Package('b'): '1.0.0',
            Package('ba'): '1.0.0',
            Package('bb'): '1.0.0',
        },
    )


def test_shared_dependencies_with_overlapping_constraints(source, check_solver_result):
    source.root_dep(Package('a'), '1.0.0')
    source.root_dep(Package('b'), '1.0.0')

    source.add(Package('a'), '1.0.0', deps={Package('shared'): '>=2.0.0,<4.0.0'})
    source.add(Package('b'), '1.0.0', deps={Package('shared'): '>=3.0.0,<5.0.0'})
    source.add(Package('shared'), '2.0.0')
    source.add(Package('shared'), '3.0.0')
    source.add(Package('shared'), '3.6.9')
    source.add(Package('shared'), '4.0.0')
    source.add(Package('shared'), '5.0.0')

    check_solver_result(
        source, {Package('a'): '1.0.0', Package('b'): '1.0.0', Package('shared'): '3.6.9'}
    )


def test_shared_dependency_where_dependent_version_affects_other_dependencies(
    source, check_solver_result
):
    source.root_dep(Package('foo'), '<=1.0.2')
    source.root_dep(Package('bar'), '1.0.0')

    source.add(Package('foo'), '1.0.0')
    source.add(Package('foo'), '1.0.1', deps={Package('bang'): '1.0.0'})
    source.add(Package('foo'), '1.0.2', deps={Package('whoop'): '1.0.0'})
    source.add(Package('foo'), '1.0.3', deps={Package('zoop'): '1.0.0'})
    source.add(Package('bar'), '1.0.0', deps={Package('foo'): '<=1.0.1'})
    source.add(Package('bang'), '1.0.0')
    source.add(Package('whoop'), '1.0.0')
    source.add(Package('zoop'), '1.0.0')

    check_solver_result(
        source, {Package('foo'): '1.0.1', Package('bar'): '1.0.0', Package('bang'): '1.0.0'}
    )


def test_circular_dependency(source, check_solver_result):
    source.root_dep(Package('foo'), '1.0.0')

    source.add(Package('foo'), '1.0.0', deps={Package('bar'): '1.0.0'})
    source.add(Package('bar'), '1.0.0', deps={Package('foo'): '1.0.0'})

    check_solver_result(source, {Package('foo'): '1.0.0', Package('bar'): '1.0.0'})


def test_override_dependency(source, check_solver_result):
    foo = Package('foo', source=WebServiceSource(registry_url='https://example.test/api'))
    bar = Package('bar', source=WebServiceSource(registry_url='https://example.test/api'))
    # cmp_local was the WebServiceSource (name with namespace),
    # but override_path changed it to the LocalSource.
    cmp_local = Package('example/cmp', source=LocalSource(path='test', override_path='test'))
    cmp_web = Package(
        'example/cmp', source=WebServiceSource(registry_url='https://example.test/api')
    )

    source.root_dep(foo, '1.0.0')
    source.add(foo, '1.0.0', deps={cmp_local: '1.1.0', bar: '2.0.0'})
    source.add(cmp_local, '1.1.0')
    source.add(bar, '2.0.0', deps={cmp_web: '1.3.0'})
    source.add(cmp_web, '1.3.0')

    source.override_dependencies(['example/cmp'])

    check_solver_result(source, {foo: '1.0.0', bar: '2.0.0', cmp_local: '1.1.0'})
