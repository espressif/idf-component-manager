# SPDX-FileCopyrightText: 2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from .integration_test_helpers import project_action


@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {
                    'dependencies': {
                        # Version intentionally not present on the registry so the
                        # solver must apply the override below to succeed.
                        'example/cmp': {
                            'version': '3.3.9~1',
                        },
                    },
                    'overrides': [
                        {
                            'example/cmp': {
                                'with': {
                                    'example/cmp-override': {
                                        'path': '../local_components/example__cmp-override',
                                        'version': '*',
                                    }
                                }
                            }
                        }
                    ],
                }
            }
        },
    ],
    indirect=True,
)
def test_reconfigure_uses_override_replacement_name_in_requirements(project):
    local_component_path = Path(project) / 'local_components' / 'example__cmp-override'
    os.makedirs(local_component_path)

    (local_component_path / 'CMakeLists.txt').write_text('idf_component_register()\n')
    (local_component_path / 'idf_component.yml').write_text('version: "2.0.0"\n')

    res = project_action(project, 'reconfigure')

    assert 'Configuring done' in res

    with open(os.path.join(project, 'dependencies.lock')) as f:
        lock = YAML(typ='safe').load(f)

    assert 'example/cmp' not in lock['dependencies']
    assert 'example/cmp-override' in lock['dependencies']
    assert lock['dependencies']['example/cmp-override']['source']['type'] == 'local'
    assert lock['dependencies']['example/cmp-override']['version'] == '2.0.0'


@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {
                    'dependencies': {
                        # A SHORT (unqualified) local dependency.
                        'cmp_orig': {
                            'path': '../local_components/cmp_orig',
                        },
                    },
                    'overrides': [
                        {
                            'cmp_orig': {
                                'with': {
                                    'repl/cmp_override': {
                                        'path': '../local_components/repl__cmp_override',
                                    }
                                }
                            }
                        }
                    ],
                }
            }
        },
    ],
    indirect=True,
)
def test_reconfigure_remaps_requirements_for_short_name_override_target(project):
    """An override whose target is a short (unqualified) ``git``/``path``
    dependency must be applied at the requirement-injection step, not only in the solver.
    """
    local_components = Path(project) / 'local_components'

    # The overridden-away original still has to exist as a valid local component so the
    # manifest's path dependency resolves while the project is being loaded.
    original_path = local_components / 'cmp_orig'
    os.makedirs(original_path)
    (original_path / 'CMakeLists.txt').write_text('idf_component_register()\n')
    (original_path / 'idf_component.yml').write_text('version: "1.0.0"\n')

    # The replacement actually built in place of ``cmp_orig``.
    replacement_path = local_components / 'repl__cmp_override'
    os.makedirs(replacement_path)
    (replacement_path / 'CMakeLists.txt').write_text('idf_component_register()\n')
    (replacement_path / 'idf_component.yml').write_text('version: "2.0.0"\n')

    res = project_action(project, 'reconfigure')

    # The override is applied in the solver regardless of the inject bug, so the lock
    # always records the replacement. Asserting it here isolates the failure below to the
    # requirement-injection step.
    with open(os.path.join(project, 'dependencies.lock')) as f:
        lock = YAML(typ='safe').load(f)

    assert 'cmp_orig' not in lock['dependencies']
    assert 'espressif/cmp_orig' not in lock['dependencies']
    assert 'repl/cmp_override' in lock['dependencies']
    assert lock['dependencies']['repl/cmp_override']['source']['type'] == 'local'
    assert lock['dependencies']['repl/cmp_override']['version'] == '2.0.0'

    # Fails on the buggy code: "Failed to resolve component 'cmp_orig'".
    assert 'Configuring done' in res, (
        'reconfigure failed - the override rename was not applied to the injected '
        'REQUIRES for the short-named target. Output:\n' + res
    )
