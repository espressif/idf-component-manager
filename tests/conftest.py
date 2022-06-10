# SPDX-FileCopyrightText: 2022 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os
import subprocess

import pytest

from idf_component_tools.hash_tools import HASH_FILENAME


@pytest.fixture()
def valid_manifest_hash():
    return '07c20149ed1f85db5660358da9aaf8b12715197f8373cca6e2f28b6ebc9eb2c8'


@pytest.fixture()
def valid_manifest():
    return {
        'version': '2.3.1~2',
        'targets': ['esp32'],
        'maintainers': ['Test Tester <test@example.com>'],
        'description': 'Test project',
        'tags': [
            'test_tag',
            'Example',
            'one_more-tag123',
        ],
        'dependencies': {
            'idf': '~4.4.4',
            'test': {
                'version': '>=8.2.0~1,<9.0.0'
            },
            'test-1': '^1.2.7',
            'test-8': {
                'version': '',
                'public': True,
            },
            'test-9': {
                'public': True,
            },
            'test-2': '',
            'test-4': '*',
            'some_component': {
                'version': '!=1.2.7'
            },
        },
        'files': {
            'include': ['**/*'],
            'exclude': ['.pyc']
        },
        'url': 'https://test.com/homepage',
        'documentation': 'https://test.com/documentation',
        'repository': 'git@github.com:test_project/test.git',
        'issues': 'https://test.com/tracker',
        'discussion': 'https://discuss.com/discuss',
    }


@pytest.fixture
def valid_optional_dependency_manifest(valid_manifest, monkeypatch):
    monkeypatch.setenv('IDF_VERSION', '5.0.0')
    monkeypatch.setenv('IDF_TARGET', 'esp32')

    valid_manifest['dependencies']['optional'] = {
        'version': '1.0.0',
        'rules': [
            {
                'if': 'idf_version >= 4.4'
            },
            {
                'if': 'target not in [esp32, esp32s2]'
            },
        ]
    }
    return valid_manifest


@pytest.fixture(scope='session')
def git_repository_with_two_branches(tmpdir_factory):
    temp_dir = tmpdir_factory.mktemp('git_repo')
    subprocess.check_output(['git', 'init', temp_dir.strpath])

    subprocess.check_output(['git', 'config', 'user.email', 'test@test.com'], cwd=temp_dir.strpath)
    subprocess.check_output(['git', 'config', 'user.name', 'Test Test'], cwd=temp_dir.strpath)

    subprocess.check_output(['git', 'checkout', '-b', 'default'], cwd=temp_dir.strpath)

    f = temp_dir.mkdir('component1').join('test_file')
    f.write(u'component1')

    subprocess.check_output(['git', 'add', '*'], cwd=temp_dir.strpath)
    subprocess.check_output(['git', 'commit', '-m', '"Init commit"'], cwd=temp_dir.strpath)

    main_commit_id = subprocess.check_output(['git', 'rev-parse', 'default'], cwd=temp_dir.strpath).strip()

    subprocess.check_output(['git', 'checkout', '-b', 'new_branch'], cwd=temp_dir.strpath)

    f = temp_dir.mkdir('component2').join('test_file')
    f.write(u'component2')

    subprocess.check_output(['git', 'add', '*'], cwd=temp_dir.strpath)
    subprocess.check_output(['git', 'commit', '-m', '"Add new branch"'], cwd=temp_dir.strpath)

    branch_commit_id = subprocess.check_output(['git', 'rev-parse', 'new_branch'], cwd=temp_dir.strpath).strip()
    subprocess.check_output(['git', 'checkout', 'default'], cwd=temp_dir.strpath)

    return {
        'path': temp_dir.strpath,
        'default_head': main_commit_id.decode('utf-8'),
        'new_branch_head': branch_commit_id.decode('utf-8')
    }


@pytest.fixture()
def tmp_managed_components(tmp_path):
    managed_components_path = tmp_path / 'managed_components'
    managed_components_path.mkdir()

    example_cmp_path = managed_components_path / 'example__cmp'
    example_cmp_path.mkdir()
    example_cmp_hash = example_cmp_path / HASH_FILENAME
    example_cmp_hash.write_text(u'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')

    mag3110_path = managed_components_path / 'mag3110'
    mag3110_path.mkdir()
    mag3110_hash = mag3110_path / HASH_FILENAME
    mag3110_hash.write_text(u'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')

    return str(managed_components_path)


@pytest.fixture(scope='session')
def pre_release_component_path():
    return os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        'fixtures',
        'components',
        'pre',
    )


@pytest.fixture(scope='session')
def release_component_path():
    return os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        'fixtures',
        'components',
        'cmp',
    )
