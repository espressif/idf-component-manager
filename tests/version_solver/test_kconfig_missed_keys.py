# SPDX-FileCopyrightText: 2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

import pytest

from idf_component_manager.version_solver.version_solver import VersionSolver
from idf_component_tools.debugger import KCONFIG_CONTEXT, SdkconfigContext
from idf_component_tools.manager import ManifestManager
from idf_component_tools.manifest import ComponentRequirement
from idf_component_tools.semver import SimpleSpec, Version
from idf_component_tools.sources import WebServiceSource
from idf_component_tools.utils import (
    ComponentWithVersions,
    HashedComponentVersion,
    ProjectRequirements,
)

MISSING_KCONFIG = 'UNSELECTED_VERSION_OPTION'


@pytest.fixture(autouse=True)
def clean_kconfig_context():
    token = KCONFIG_CONTEXT.set(SdkconfigContext())
    yield
    KCONFIG_CONTEXT.reset(token)


@pytest.fixture
def fake_registry(monkeypatch):
    comp_a_1_0_0 = HashedComponentVersion('1.0.0', component_hash='a' * 64)
    comp_a_1_0_1 = HashedComponentVersion(
        '1.0.1',
        component_hash='b' * 64,
        dependencies=[
            ComponentRequirement(
                name='test/missing',
                version='*',
                matches=[{'if': f'$CONFIG{{{MISSING_KCONFIG}}} == True'}],
            )
        ],
    )
    comp_b_1_0_0 = HashedComponentVersion(
        '1.0.0',
        component_hash='c' * 64,
        dependencies=[ComponentRequirement(name='test/comp_a', version='*')],
    )

    comp_c_1_0_0 = HashedComponentVersion(
        '1.0.0',
        component_hash='d' * 64,
        dependencies=[ComponentRequirement(name='test/comp_a', version='>=1.0.0,<1.0.1')],
    )

    versions_by_name = {
        'test/comp_a': [comp_a_1_0_0, comp_a_1_0_1],
        'test/comp_b': [comp_b_1_0_0],
        'test/comp_c': [comp_c_1_0_0],
    }

    def versions(self, name, spec='*', target=None):  # noqa: ARG001
        required_spec = SimpleSpec(spec or '*')
        versions = [
            version
            for version in versions_by_name[name]
            if required_spec.match(Version(str(version)))
        ]
        return ComponentWithVersions(name, versions)

    monkeypatch.setattr(WebServiceSource, 'versions', versions)


def load_project_manifest(tmp_path: Path, manifest_text: str):
    main_dir = tmp_path / 'main'
    main_dir.mkdir()
    (main_dir / 'idf_component.yml').write_text(manifest_text)
    return ManifestManager(str(main_dir), 'main').load()


@pytest.mark.usefixtures('fake_registry')
def test_unselected_candidate_missing_kconfig_is_not_reported(tmp_path, monkeypatch):
    monkeypatch.setenv('IDF_TARGET', 'esp32')
    manifest = load_project_manifest(
        tmp_path,
        """dependencies:
  test/comp_a: 1.0.0
  test/comp_b: '*'
""",
    )

    solution = VersionSolver(ProjectRequirements([manifest])).solve()

    assert str(solution.solved_components['test/comp_a'].version) == '1.0.0'
    assert MISSING_KCONFIG not in KCONFIG_CONTEXT.get().missed_keys


@pytest.mark.usefixtures('fake_registry')
def test_selected_candidate_missing_kconfig_is_reported(tmp_path, monkeypatch):
    monkeypatch.setenv('IDF_TARGET', 'esp32')
    manifest = load_project_manifest(
        tmp_path,
        """dependencies:
  test/comp_a: '*'
""",
    )

    solution = VersionSolver(ProjectRequirements([manifest])).solve()

    assert str(solution.solved_components['test/comp_a'].version) == '1.0.1'
    assert MISSING_KCONFIG in KCONFIG_CONTEXT.get().missed_keys


@pytest.mark.usefixtures('fake_registry')
def test_evaluated_but_rejected_candidate_missing_kconfig_is_not_reported(tmp_path, monkeypatch):
    """Both comp_a 1.0.0 and 1.0.1 are evaluated as candidates (spec is '*'),
    but comp_c constrains comp_a to <1.0.1, forcing the solver to pick 1.0.0.
    The missing Kconfig key from the rejected 1.0.1 must not leak into the global context."""
    monkeypatch.setenv('IDF_TARGET', 'esp32')
    manifest = load_project_manifest(
        tmp_path,
        """dependencies:
  test/comp_a: '*'
  test/comp_c: '*'
""",
    )

    solution = VersionSolver(ProjectRequirements([manifest])).solve()

    assert str(solution.solved_components['test/comp_a'].version) == '1.0.0'
    assert MISSING_KCONFIG not in KCONFIG_CONTEXT.get().missed_keys
