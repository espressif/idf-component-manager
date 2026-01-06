# SPDX-FileCopyrightText: 2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
"""Test that local components have higher precedence when resolving dependencies."""

import pytest
from ruamel.yaml import YAML

from idf_component_manager.version_solver.version_solver import VersionSolver
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


def create_component(parent_dir, name, version='1.0.0', dependencies=None):
    """Helper to create a component with manifest."""
    comp_dir = parent_dir / name.replace('/', '__')
    comp_dir.mkdir()

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
