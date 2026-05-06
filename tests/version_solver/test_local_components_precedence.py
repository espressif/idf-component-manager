# SPDX-FileCopyrightText: 2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
"""Test that local components have higher precedence when resolving dependencies."""

import logging

import pytest
from ruamel.yaml import YAML

from idf_component_manager.version_solver.version_solver import VersionSolver
from idf_component_tools import LOGGING_NAMESPACE
from idf_component_tools.manager import ManifestManager
from idf_component_tools.sources import LocalSource
from idf_component_tools.utils import ProjectRequirements


@pytest.fixture
def project_structure(tmp_path, monkeypatch):
    monkeypatch.setenv('IDF_TARGET', 'esp32')
    project_dir = tmp_path / 'project'
    main_dir = project_dir / 'main'
    components_dir = project_dir / 'components'

    for dir in (main_dir, components_dir):
        dir.mkdir(parents=True)

    return main_dir, components_dir


def create_component(parent_dir, name, version='1.0.0', dependencies=None, raw=None):
    """Helper to create a component with manifest.

    Pass ``raw`` to write a verbatim ``idf_component.yml`` (useful for conditional
    ``rules``/``matches`` that the structured ``dependencies`` argument cannot express).
    """
    comp_dir = parent_dir / name.replace('/', '__')
    comp_dir.mkdir()

    if raw is not None:
        (comp_dir / 'idf_component.yml').write_text(raw)
        return comp_dir

    manifest_data = {'version': version}
    if dependencies:
        manifest_data['dependencies'] = dependencies

    yaml = YAML()
    yaml.dump(manifest_data, comp_dir / 'idf_component.yml')
    return comp_dir


def load_manifests(main_dir, *component_dirs):
    """Helper to load manifests from main and component directories."""
    manifests = [ManifestManager(str(main_dir), 'main').load()]
    for comp_dir in component_dirs:
        name = comp_dir.name
        manifests.append(ManifestManager(str(comp_dir), name).load())
    return manifests


def assert_all_local(solution, *component_names):
    """Assert that all specified components are resolved as LocalSource."""
    for name in component_names:
        assert name in solution.solved_components, f'{name} not in solution'
        assert isinstance(solution.solved_components[name].source, LocalSource), (
            f'{name} not resolved as local'
        )


def test_local_component_transitive_dependency(project_structure):
    """
    Test: main → A → B (both A and B are local)

    Verifies that when local component A depends on B, and B exists locally,
    the solver correctly resolves both as local components.
    """
    main_dir, components_dir = project_structure

    (main_dir / 'idf_component.yml').write_text('dependencies:\n  espressif/comp_a: "*"\n')

    comp_a = create_component(
        components_dir, 'espressif/comp_a', dependencies={'espressif/comp_b': '*', 'idf': '>=5.0'}
    )
    comp_b = create_component(components_dir, 'espressif/comp_b', dependencies={'idf': '>=5.0'})

    manifests = load_manifests(main_dir, comp_a, comp_b)
    project_requirements = ProjectRequirements(manifests)

    solver = VersionSolver(project_requirements)
    solution = solver.solve()

    assert_all_local(solution, 'espressif/comp_a', 'espressif/comp_b')


def test_local_component_chain_dependency(project_structure):
    """
    Test: main → A → B → C (all local)

    Verifies that the solver correctly handles a chain of local component
    dependencies where each component depends on the next.
    """
    main_dir, components_dir = project_structure

    (main_dir / 'idf_component.yml').write_text('dependencies:\n  test/comp_a: "*"\n')

    comp_a = create_component(
        components_dir, 'test/comp_a', dependencies={'test/comp_b': '*', 'idf': '>=5.0'}
    )
    comp_b = create_component(
        components_dir, 'test/comp_b', dependencies={'test/comp_c': '*', 'idf': '>=5.0'}
    )
    comp_c = create_component(components_dir, 'test/comp_c', dependencies={'idf': '>=5.0'})

    manifests = load_manifests(main_dir, comp_a, comp_b, comp_c)
    project_requirements = ProjectRequirements(manifests)

    solver = VersionSolver(project_requirements)
    solution = solver.solve()

    assert_all_local(solution, 'test/comp_a', 'test/comp_b', 'test/comp_c')


def test_override_replaces_transitive_dependency_with_local_source(project_structure):
    main_dir, components_dir = project_structure
    overrides_dir = main_dir.parent / 'overrides'
    overrides_dir.mkdir()

    (main_dir / 'idf_component.yml').write_text(
        'dependencies:\n'
        '  test/comp_a: "*"\n'
        'overrides:\n'
        '  - test/comp_b:\n'
        '      with:\n'
        '        test/comp_b_override:\n'
        '          path: ../overrides/test__comp_b\n'
        '          version: "*"\n'
    )

    comp_a = create_component(
        components_dir, 'test/comp_a', dependencies={'test/comp_b': '*', 'idf': '>=5.0'}
    )
    create_component(overrides_dir, 'test/comp_b', version='2.0.0', dependencies={'idf': '>=5.0'})

    manifests = load_manifests(main_dir, comp_a)
    project_requirements = ProjectRequirements(manifests)

    solver = VersionSolver(project_requirements)
    solution = solver.solve()

    assert_all_local(solution, 'test/comp_a', 'test/comp_b_override')
    assert 'test/comp_b' not in solution.solved_components
    assert solution.solved_components['test/comp_b_override'].version == '2.0.0'


def test_short_override_target_matches_short_local_dependency(project_structure):
    main_dir, components_dir = project_structure
    overrides_dir = main_dir.parent / 'overrides'
    overrides_dir.mkdir()

    (main_dir / 'idf_component.yml').write_text(
        'dependencies:\n'
        '  comp_a:\n'
        '    path: ../components/comp_a\n'
        'overrides:\n'
        '  - comp_a:\n'
        '      with:\n'
        '        comp_a_override:\n'
        '          path: ../overrides/comp_a_override\n'
        '          version: "*"\n'
    )
    create_component(components_dir, 'comp_a', dependencies={'idf': '>=5.0'})
    create_component(overrides_dir, 'comp_a_override', dependencies={'idf': '>=5.0'})

    manifests = load_manifests(main_dir)
    project_requirements = ProjectRequirements(manifests)

    solver = VersionSolver(project_requirements)
    solution = solver.solve()

    assert_all_local(solution, 'comp_a_override')
    assert 'comp_a' not in solution.solved_components


def test_short_override_target_matches_short_git_dependency(project_structure):
    main_dir, _components_dir = project_structure
    overrides_dir = main_dir.parent / 'overrides'
    overrides_dir.mkdir()

    (main_dir / 'idf_component.yml').write_text(
        'dependencies:\n'
        '  my_git:\n'
        '    git: https://github.com/my-org/tinyusb-fork.git\n'
        '    path: .\n'
        '    version: my-fix-branch\n'
        'overrides:\n'
        '  - my_git:\n'
        '      with:\n'
        '        my_override_local:\n'
        '          path: ../overrides/my_override_local\n'
    )
    create_component(overrides_dir, 'my_override_local', dependencies={'idf': '>=5.0'})

    manifests = load_manifests(main_dir)
    project_requirements = ProjectRequirements(manifests)

    solver = VersionSolver(project_requirements)
    solution = solver.solve()

    assert_all_local(solution, 'my_override_local')
    assert 'my_git' not in solution.solved_components


def test_direct_dependency_override(
    project_structure,
    caplog,
):
    caplog.set_level(logging.DEBUG, logger=LOGGING_NAMESPACE)
    main_dir, _components_dir = project_structure
    overrides_dir = main_dir.parent / 'overrides'
    overrides_dir.mkdir()

    (main_dir / 'idf_component.yml').write_text(
        'dependencies:\n'
        '  test/comp_b: "*"\n'
        'overrides:\n'
        '  - test/comp_b:\n'
        '      with:\n'
        '        test/comp_b_override:\n'
        '          path: ../overrides/test__comp_b\n'
        '          version: "*"\n'
    )
    create_component(overrides_dir, 'test/comp_b', version='2.0.0', dependencies={'idf': '>=5.0'})

    manifests = load_manifests(main_dir)
    project_requirements = ProjectRequirements(manifests)

    solver = VersionSolver(project_requirements)
    solution = solver.solve()

    assert_all_local(solution, 'test/comp_b_override')
    assert 'test/comp_b' not in solution.solved_components
    assert (
        'Applying override for dependency "test/comp_b", specified in {}'.format(
            main_dir / 'idf_component.yml'
        )
        in caplog.text
    )


def test_override_declared_in_local_path_dependency_manifest_is_ignored(project_structure):
    main_dir, _components_dir = project_structure
    external_dir = main_dir.parent / 'external'
    external_dir.mkdir()

    (main_dir / 'idf_component.yml').write_text(
        'dependencies:\n  test/comp_a:\n    path: ../external/test__comp_a\n'
    )

    comp_a = create_component(external_dir, 'test/comp_a', dependencies={'idf': '>=5.0'})
    (comp_a / 'idf_component.yml').write_text(
        'version: 1.0.0\n'
        'dependencies:\n'
        '  idf: ">=5.0"\n'
        'overrides:\n'
        '  - test/comp_b:\n'
        '      with:\n'
        '        test/comp_b_override:\n'
        '          path: ../../overrides/test__comp_b\n'
        '          version: "*"\n'
    )

    manifests = load_manifests(main_dir)
    project_requirements = ProjectRequirements(manifests)

    assert project_requirements.override_rules == {}


def test_overrides_in_local_path_dependency_manifest_do_not_conflict(project_structure):
    main_dir, _components_dir = project_structure
    external_dir = main_dir.parent / 'external'
    external_dir.mkdir()

    (main_dir / 'idf_component.yml').write_text(
        'dependencies:\n  test/comp_a:\n    path: ../external/test__comp_a\noverrides: []\n'
    )

    comp_a = create_component(external_dir, 'test/comp_a', dependencies={'idf': '>=5.0'})
    (comp_a / 'idf_component.yml').write_text(
        'version: 1.0.0\ndependencies:\n  idf: ">=5.0"\noverrides: []\n'
    )

    manifests = load_manifests(main_dir)
    project_requirements = ProjectRequirements(manifests)

    assert project_requirements.override_rules == {}


def test_override_can_be_declared_in_component_manifest(project_structure):
    main_dir, components_dir = project_structure
    overrides_dir = main_dir.parent / 'overrides'
    overrides_dir.mkdir()

    (main_dir / 'idf_component.yml').write_text('dependencies:\n  test/comp_a: "*"\n')

    comp_a = create_component(
        components_dir, 'test/comp_a', dependencies={'test/comp_b': '*', 'idf': '>=5.0'}
    )
    (comp_a / 'idf_component.yml').write_text(
        'version: 1.0.0\n'
        'dependencies:\n'
        '  test/comp_b: "*"\n'
        '  idf: ">=5.0"\n'
        'overrides:\n'
        '  - test/comp_b:\n'
        '      with:\n'
        '        test/comp_b_override:\n'
        '          path: ../../overrides/test__comp_b\n'
        '          version: "*"\n'
    )
    create_component(overrides_dir, 'test/comp_b', version='2.0.0', dependencies={'idf': '>=5.0'})

    manifests = load_manifests(main_dir, comp_a)
    project_requirements = ProjectRequirements(manifests)

    solver = VersionSolver(project_requirements)
    solution = solver.solve()

    assert_all_local(solution, 'test/comp_a', 'test/comp_b_override')
    assert 'test/comp_b' not in solution.solved_components


def test_override_notice_is_not_duplicated(project_structure, caplog):
    caplog.set_level(logging.DEBUG, logger=LOGGING_NAMESPACE)
    main_dir, components_dir = project_structure
    overrides_dir = main_dir.parent / 'overrides'
    overrides_dir.mkdir()

    (main_dir / 'idf_component.yml').write_text(
        'dependencies:\n'
        '  test/comp_a: "*"\n'
        'overrides:\n'
        '  - test/comp_b:\n'
        '      with:\n'
        '        test/comp_b_override:\n'
        '          path: ../overrides/test__comp_b\n'
        '          version: "*"\n'
    )

    comp_a = create_component(
        components_dir, 'test/comp_a', dependencies={'test/comp_b': '*', 'idf': '>=5.0'}
    )
    create_component(overrides_dir, 'test/comp_b', version='2.0.0', dependencies={'idf': '>=5.0'})

    manifests = load_manifests(main_dir, comp_a)
    project_requirements = ProjectRequirements(manifests)

    solver = VersionSolver(project_requirements)
    solver.solve()

    override_messages = [
        record.message
        for record in caplog.records
        if record.message.startswith('Applying override for dependency "test/comp_b"')
    ]

    assert override_messages == [
        'Applying override for dependency "test/comp_b" (introduced by component "test/comp_a")'
    ]


def test_unused_override_warning(project_structure, caplog):
    """
    Test that a warning is emitted when an override targets a component
    that never appears in the dependency graph.
    """
    caplog.set_level(logging.DEBUG, logger=LOGGING_NAMESPACE)
    main_dir, components_dir = project_structure

    (main_dir / 'idf_component.yml').write_text(
        'dependencies:\n'
        '  idf: ">=5.0"\n'
        'overrides:\n'
        '  - espressif/nonexistent:\n'
        '      with:\n'
        '        espressif/replacement:\n'
        '          version: "*"\n'
    )

    manifests = load_manifests(main_dir)
    project_requirements = ProjectRequirements(manifests)

    solver = VersionSolver(project_requirements)
    solver.solve()

    assert 'Override for "espressif/nonexistent" was not used' in caplog.text


def test_unused_short_override_warning_is_not_duplicated(project_structure, caplog):
    """
    Each override is registered under a single canonical key (``espressif/nonexistent``
    here) and lookups normalize the requirement name, so there is no per-alias
    duplication. This guards against reintroducing an alias scheme that would emit the
    "was not used" notice once per alias.
    """
    caplog.set_level(logging.DEBUG, logger=LOGGING_NAMESPACE)
    main_dir, _components_dir = project_structure

    (main_dir / 'idf_component.yml').write_text(
        'dependencies:\n'
        '  idf: ">=5.0"\n'
        'overrides:\n'
        '  - nonexistent:\n'
        '      with:\n'
        '        espressif/replacement:\n'
        '          version: "*"\n'
    )

    manifests = load_manifests(main_dir)
    VersionSolver(ProjectRequirements(manifests)).solve()

    unused_messages = [
        record.message for record in caplog.records if 'was not used' in record.message
    ]

    assert unused_messages == [
        'Override for "nonexistent" was not used - '
        'this component was not found in the dependency graph'
    ]


def test_override_keeps_conditional_transitive_dependency_conditional(project_structure):
    """Regression test for the review finding that overriding a dependency discarded the
    ``rules``/``matches`` conditions of the original (transitive) edge, pulling the
    replacement into the build on every target.

    ``comp_a`` declares ``comp_b`` only for ``esp32s3``; the project target is ``esp32``,
    so the override must stay inactive and ``comp_b`` must not be solved.
    """
    main_dir, components_dir = project_structure
    overrides_dir = main_dir.parent / 'overrides'
    overrides_dir.mkdir()

    (main_dir / 'idf_component.yml').write_text(
        'dependencies:\n'
        '  test/comp_a:\n'
        '    path: ../components/test__comp_a\n'
        'overrides:\n'
        '  - test/comp_b:\n'
        '      with:\n'
        '        test/comp_b:\n'
        '          path: ../overrides/test__comp_b\n'
        '          version: "*"\n'
    )
    create_component(
        components_dir,
        'test/comp_a',
        raw=(
            'version: 1.0.0\n'
            'dependencies:\n'
            '  idf: ">=5.0"\n'
            '  test/comp_b:\n'
            '    version: "*"\n'
            '    rules:\n'
            '      - if: "target == esp32s3"\n'
        ),
    )
    create_component(overrides_dir, 'test/comp_b', version='2.0.0', dependencies={'idf': '>=5.0'})

    manifests = load_manifests(main_dir)
    solution = VersionSolver(ProjectRequirements(manifests)).solve()

    assert 'test/comp_a' in solution.solved_components
    assert 'test/comp_b' not in solution.solved_components


def test_local_components_dir_shadows_override(project_structure, caplog):
    """A component in the project ``components`` directory has the highest priority in the
    ESP-IDF build system (``project_components`` override ``project_managed_components``),
    so it wins over an override targeting the same name.

    The override redirects ``test/comp_b`` to ``../overrides`` (v2.0.0); a same-named
    component also lives in ``components/`` (v9.9.9). The local component must win in the
    resolved graph and the override must be reported as *shadowed* (not as "applied").
    """
    caplog.set_level(logging.DEBUG, logger=LOGGING_NAMESPACE)
    main_dir, components_dir = project_structure
    overrides_dir = main_dir.parent / 'overrides'
    overrides_dir.mkdir()
    external_dir = main_dir.parent / 'external'
    external_dir.mkdir()

    (main_dir / 'idf_component.yml').write_text(
        'dependencies:\n'
        '  test/comp_a:\n'
        '    path: ../external/test__comp_a\n'
        'overrides:\n'
        '  - test/comp_b:\n'
        '      with:\n'
        '        test/comp_b:\n'
        '          path: ../overrides/test__comp_b\n'
        '          version: "*"\n'
    )
    create_component(external_dir, 'test/comp_a', dependencies={'test/comp_b': '*', 'idf': '>=5.0'})
    # Same-named local component in components/ with a different version.
    create_component(components_dir, 'test/comp_b', version='9.9.9', dependencies={'idf': '>=5.0'})
    # The override replacement (must not win over the components/ copy).
    create_component(overrides_dir, 'test/comp_b', version='2.0.0', dependencies={'idf': '>=5.0'})

    manifests = load_manifests(main_dir, components_dir / 'test__comp_b')
    solution = VersionSolver(ProjectRequirements(manifests)).solve()

    # The components/ directory wins, mirroring ESP-IDF's CMake component precedence.
    assert solution.solved_components['test/comp_b'].version == '9.9.9'
    # The override for comp_b is reported as shadowed by the local component, not as
    # "applied" (asserting on the comp_b edge specifically, not comp_a's path notice).
    assert (
        'Override for dependency "test/comp_b" is ignored because a component placed at'
        in caplog.text
    )
    assert 'takes precedence' in caplog.text
    assert 'Applying override for dependency "test/comp_b"' not in caplog.text
