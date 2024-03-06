# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os
import shutil
from pathlib import Path

import pytest

from .integration_test_helpers import project_action


@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'example/cmp': {
                            'version': '>=3.3.5',
                        },
                    }
                }
            }
        },
    ],
    indirect=True,
)
def test_changes_in_component(project):
    res = project_action(project, 'reconfigure')
    assert 'Build files have been written to' in res

    with open(os.path.join(project, 'managed_components', 'example__cmp', 'README.md'), 'w') as f:
        f.write('TEST STRING')
    shutil.rmtree(os.path.join(project, 'build'))
    res = project_action(project, 'reconfigure')

    assert 'in the "managed_components" directory' in res

    shutil.move(
        os.path.join(project, 'managed_components', 'example__cmp'),
        os.path.join(project, 'components', 'example__cmp'),
    )
    res = project_action(project, 'reconfigure')

    assert 'Build files have been written to' in res

    shutil.move(
        os.path.join(project, 'components', 'example__cmp'),
        os.path.join(project, 'components', 'cmp'),
    )
    res = project_action(project, 'reconfigure')

    assert 'Build files have been written to' in res


@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'example/cmp': {
                            'version': '^3.3.0',
                        }
                    }
                }
            }
        },
    ],
    indirect=True,
)
def test_fullclean_managed_components(project):
    project_action(project, 'reconfigure')
    assert Path(project, 'managed_components').is_dir()
    project_action(project, 'fullclean')
    assert not Path(project, 'managed_components').is_dir()
    project_action(project, 'reconfigure')
    component_hash = Path(project, 'managed_components', 'example__cmp', '.component_hash')
    with component_hash.open(mode='wt') as hash_file:
        hash_file.write('e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')
    project_action(project, 'fullclean')
    assert Path(project, 'managed_components', 'example__cmp').is_dir()


@pytest.mark.parametrize(
    'project,result',
    [
        (
            {
                'components': {
                    'main': {
                        'dependencies': {
                            'test/component_with_exclude_for_component_hash': {
                                'version': '0.3.2',  # version without exclude
                            },
                        }
                    }
                }
            },
            'directory were modified on the disk since the last',
        ),
        (
            {
                'components': {
                    'main': {
                        'dependencies': {
                            'test/component_with_exclude_for_component_hash': {
                                'version': '0.3.3',  # version with exclude
                            },
                        }
                    }
                }
            },
            'Build files have been written to',
        ),
    ],
    indirect=True,
)
def test_component_hash_exclude_built_files(project, result):
    res = project_action(project, 'build')
    assert 'Project build complete' in res

    res = project_action(project, 'reconfigure')
    assert result in res
