# SPDX-FileCopyrightText: 2023-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import hashlib
import os
import re
import shutil
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from idf_component_tools.lock import LockManager
from integration_tests.integration_test_helpers import project_action


@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'main': {
                    'dependencies': {
                        'example/cmp': {'version': '*'},
                    }
                }
            }
        },
    ],
    indirect=True,
)
def test_download_component_hash_different_from_lock_file(project):
    res = project_action(project, 'reconfigure')
    assert 'Configuring done' in res

    # remove managed_components and modify the dependencies.lock file hash
    shutil.rmtree(os.path.join(project, 'managed_components'))

    lock_path = str(Path(project) / 'dependencies.lock')
    with open(lock_path) as fr:
        file_str = fr.read()

    component_hash_line_regex = re.compile('component_hash: .+$', re.MULTILINE)
    with open(lock_path, 'w') as fw:
        fw.write(
            component_hash_line_regex.sub(
                'component_hash: {}'.format(hashlib.sha256(b'foobar').hexdigest()), file_str
            )
        )

    res = project_action(project, 'reconfigure')
    assert 'spoof' in res


@pytest.mark.parametrize(
    'project',
    [
        {'components': {'main': {}}},
    ],
    indirect=True,
)
def test_lock_file_include_idf_without_explicit_idf_dependency(project):
    (Path(project) / 'main' / 'idf_component.yml').touch()

    res = project_action(project, 'reconfigure')
    assert 'Configuring done' in res

    solution = LockManager(str(Path(project) / 'dependencies.lock')).load()
    assert solution.dependencies[0].name == 'idf'


@pytest.mark.parametrize(
    'project',
    [
        {'components': {'main': {}}},
    ],
    indirect=True,
)
def test_lock_version_mismatch(monkeypatch, project):
    monkeypatch.setenv('IDF_TARGET', 'esp32')
    lock_path = os.path.join(str(project), 'dependencies.lock')
    (Path(project) / 'main' / 'idf_component.yml').touch()

    simple_lock = {
        'dependencies': {
            'idf': {
                'source': {
                    'type': 'idf',
                },
                'version': '10.0.0',
            }
        },
        'manifest_hash': 'f' * 64,
        'target': 'esp32',
        'version': '1.0.0',
    }

    with open(lock_path, 'w') as fw:
        YAML(typ='safe').dump(simple_lock, fw)

    res = project_action(project, 'reconfigure')
    assert 'Recreating lock file with the current version' in res

    with open(lock_path) as fr:
        lock = YAML(typ='safe').load(fr)

    assert lock['version'] == '2.0.0'
