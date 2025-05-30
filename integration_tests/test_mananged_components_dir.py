# SPDX-FileCopyrightText: 2022-2025 Espressif Systems (Shanghai) CO LTD
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
def test_changes_in_component(project, monkeypatch):
    res = project_action(project, 'reconfigure')
    assert 'Build files have been written to' in res

    with open(os.path.join(project, 'managed_components', 'example__cmp', 'cmp.c'), 'a') as f:
        f.write('// just a comment')

    # .component_hash same, no error
    res = project_action(project, 'reconfigure')
    assert 'Configuring done' in res

    # error when in strict mode
    monkeypatch.setenv('IDF_COMPONENT_STRICT_CHECKSUM', 'y')
    res = project_action(project, 'reconfigure')
    assert 'in the "managed_components" directory' in res
    assert 'Configuring done' not in res
    monkeypatch.delenv('IDF_COMPONENT_STRICT_CHECKSUM')

    shutil.move(
        os.path.join(project, 'managed_components', 'example__cmp'),
        os.path.join(project, 'components', 'example__cmp'),
    )
    res = project_action(project, 'reconfigure')
    assert 'Configuring done' in res

    shutil.move(
        os.path.join(project, 'components', 'example__cmp'),
        os.path.join(project, 'components', 'cmp'),
    )

    # change lock file path
    with open(os.path.join(project, 'dependencies.lock'), 'w+') as fw:
        file_str = fw.read()
        fw.seek(0)
        old_str = f'path: {os.path.join(project, "components", "example__cmp")}'
        new_str = f'path: {os.path.join(project, "components", "cmp")}'
        fw.write(file_str.replace(old_str, new_str))

    res = project_action(project, 'reconfigure')
    assert 'Configuring done' in res


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

    # Create new file and fullclean
    with open(os.path.join(project, 'managed_components', 'example__cmp', 'test_file'), 'w') as f:
        f.write('test file')

    project_action(project, 'fullclean')
    assert not Path(project, 'managed_components', 'example__cmp').is_dir()
    project_action(project, 'reconfigure')

    # Remove CHECKSUMS.json to test different behavior
    os.remove(os.path.join(project, 'managed_components', 'example__cmp', 'CHECKSUMS.json'))

    # Create new file again and fullclean
    with open(os.path.join(project, 'managed_components', 'example__cmp', 'test_file'), 'w') as f:
        f.write('test file')

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
            'Configuring done',
        ),
    ],
    indirect=True,
)
def test_component_hash_exclude_built_files(project, result, monkeypatch):
    res = project_action(project, 'reconfigure')
    assert 'Configuring done' in res

    res = project_action(project, 'reconfigure')
    assert 'Configuring done' in res

    monkeypatch.setenv('IDF_COMPONENT_STRICT_CHECKSUM', 'y')
    res = project_action(project, 'reconfigure')
    assert 'Configuring done' in res

    os.remove(
        os.path.join(
            project,
            'managed_components',
            'test__component_with_exclude_for_component_hash',
            'CHECKSUMS.json',
        )
    )
    res = project_action(project, 'reconfigure')
    assert result in res
