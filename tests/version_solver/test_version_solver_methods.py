# SPDX-FileCopyrightText: 2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import pytest

from idf_component_manager.version_solver.mixology.package import Package
from idf_component_manager.version_solver.version_solver import VersionSolver
from idf_component_tools.debugger import KCONFIG_CONTEXT, SdkconfigContext
from idf_component_tools.sources.web_service import WebServiceSource
from idf_component_tools.utils import ProjectRequirements


@pytest.fixture(autouse=True)
def clean_kconfig_context():
    token = KCONFIG_CONTEXT.set(SdkconfigContext())
    yield
    KCONFIG_CONTEXT.reset(token)


@pytest.fixture
def solver():
    return VersionSolver(ProjectRequirements([]))


def test_candidate_key():
    pkg = Package('test', WebServiceSource())

    class FakeVersion:
        def __init__(self, v, h):
            self.v = v
            self.component_hash = h

        def __str__(self):
            return self.v

    v = FakeVersion('1.0.0', 'hash123')
    key = VersionSolver._candidate_key(pkg, v)
    assert key == (pkg, '1.0.0', 'hash123')

    v_no_hash = FakeVersion('2.0.0', None)
    key_no_hash = VersionSolver._candidate_key(pkg, v_no_hash)
    assert key_no_hash == (pkg, '2.0.0', None)


def test_collect_candidate_missed_kconfigs(solver):
    pkg = Package('test', WebServiceSource())
    kconfig_ctx = KCONFIG_CONTEXT.get()

    # Initial global state
    kconfig_ctx.missed_keys['A'].add('req1')

    class FakeVersion:
        component_hash = None

        def __str__(self):
            return '1.0.0'

    version = FakeVersion()

    with solver._collect_candidate_missed_kconfigs(pkg, version):
        # Simulate evaluating an optional dependency missing some keys
        kconfig_ctx.missed_keys['A'].add('req2')
        kconfig_ctx.missed_keys['B'].add('req3')

    # Global context should be completely restored
    assert kconfig_ctx.missed_keys['A'] == {'req1'}
    assert 'B' not in kconfig_ctx.missed_keys

    # Internal state should capture the delta (req2 and req3)
    candidate_key = VersionSolver._candidate_key(pkg, version)
    assert candidate_key in solver._candidate_missed_kconfigs
    misses = solver._candidate_missed_kconfigs[candidate_key]
    assert misses['A'] == {'req2'}
    assert misses['B'] == {'req3'}


def test_commit_selected_candidate_missed_kconfigs(solver):
    pkg1 = Package('test1', WebServiceSource())
    pkg2 = Package('test2', WebServiceSource())

    class FakeVersion:
        component_hash = None

        def __init__(self, v):
            self.v = v

        def __str__(self):
            return self.v

    v1 = FakeVersion('1.0.0')
    v2 = FakeVersion('2.0.0')

    # Seed the hidden internal state
    solver._candidate_missed_kconfigs[VersionSolver._candidate_key(pkg1, v1)] = {'A': {'req1'}}
    solver._candidate_missed_kconfigs[VersionSolver._candidate_key(pkg2, v2)] = {'B': {'req2'}}

    # Decisions only include pkg1
    decisions = {
        Package.root(): '0.0.0',  # Root must be ignored by the logic
        pkg1: v1,
    }

    solver._commit_selected_candidate_missed_kconfigs(decisions)

    kconfig_ctx = KCONFIG_CONTEXT.get()

    # pkg1 was selected, so 'A' should be committed
    assert 'A' in kconfig_ctx.missed_keys
    assert kconfig_ctx.missed_keys['A'] == {'req1'}

    # pkg2 was NOT in decisions, so 'B' should not be committed
    assert 'B' not in kconfig_ctx.missed_keys
