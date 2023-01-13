# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os
import shutil
from io import open
from pathlib import Path

import pytest

from .integration_test_helpers import project_action


@pytest.mark.parametrize(
    'project', [
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
    indirect=True)
def test_changes_in_component(project):
    res = project_action(project, 'reconfigure')
    assert 'Build files have been written to' in res

    with open(os.path.join(project, 'managed_components', 'example__cmp', 'README.md'), 'w') as f:
        f.write(u'TEST STRING')
    shutil.rmtree(os.path.join(project, 'build'))
    res = project_action(project, 'reconfigure')

    assert 'in the "managed_components" directory' in res

    shutil.move(
        os.path.join(project, 'managed_components', 'example__cmp'),
        os.path.join(project, 'components', 'example__cmp'))
    res = project_action(project, 'reconfigure')

    assert 'Build files have been written to' in res

    shutil.move(os.path.join(project, 'components', 'example__cmp'), os.path.join(project, 'components', 'cmp'))
    res = project_action(project, 'reconfigure')

    assert 'Build files have been written to' in res


@pytest.mark.parametrize(
    'project', [
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
    ], indirect=True)
def test_fullclean_managed_components(project):
    project_action(project, 'reconfigure')
    assert Path(project, 'managed_components').is_dir()
    project_action(project, 'fullclean')
    assert not Path(project, 'managed_components').is_dir()
    project_action(project, 'reconfigure')
    component_hash = Path(project, 'managed_components', 'example__cmp', '.component_hash')
    with component_hash.open(mode='wt') as hash_file:
        hash_file.write(u'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')
    project_action(project, 'fullclean')
    assert Path(project, 'managed_components', 'example__cmp').is_dir()
