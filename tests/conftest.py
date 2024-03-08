# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os
import typing as t
from pathlib import Path

import pytest
import requests_mock

from idf_component_tools.hash_tools.constants import HASH_FILENAME


@pytest.fixture()
def file_with_size():
    def file_builder(path: t.Union[str, Path], size: int) -> None:
        with open(str(path), 'w') as f:
            f.write('x' * size)

    return file_builder


@pytest.fixture()
def valid_manifest_hash():
    return '7169f4c78d49021379e0df0e288440ab2df1cf694119b56d5c5bac22ef7833ab'


@pytest.fixture(autouse=True)
def monkeypatch_idf_version(monkeypatch):
    monkeypatch.setenv('IDF_VERSION', '5.3.0')


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
            'test': {'version': '>=8.2.0~1,<9.0.0'},
            'test-1': '^1.2.7',
            'test-8': {
                'version': '*',
                'public': True,
            },
            'test-9': {
                'public': True,
            },
            'test-2': '*',
            'test-4': '*',
            'some_component': {'version': '!=1.2.7'},
        },
        'files': {'include': ['**/*'], 'exclude': ['.pyc']},
        'url': 'https://test.com/homepage',
        'documentation': 'https://test.com/documentation',
        'repository': 'git@github.com:test_project/test.git',
        'issues': 'https://test.com/tracker',
        'discussion': 'https://discuss.com/discuss',
    }


@pytest.fixture(autouse=True)
def disable_cache(monkeypatch):
    """Disable cache for all tests."""
    monkeypatch.setenv('IDF_COMPONENT_API_CACHE_EXPIRATION_MINUTES', '0')


@pytest.fixture
def valid_optional_dependency_manifest(valid_manifest):
    valid_manifest['dependencies']['optional'] = {
        'version': '1.0.0',
        'matches': [
            {
                'if': 'idf_version >= 4.4',
                'version': '2.0.0',
            },
        ],
        'rules': [
            {'if': 'idf_version >= 4.4'},
            {'if': 'target not in [esp32, esp32s2]'},
        ],
    }
    return valid_manifest


@pytest.fixture
def valid_optional_dependency_manifest_with_idf(valid_optional_dependency_manifest, monkeypatch):
    monkeypatch.setenv('IDF_VERSION', '5.0.0')
    monkeypatch.setenv('IDF_TARGET', 'esp32')

    return valid_optional_dependency_manifest


@pytest.fixture()
def tmp_managed_components(tmp_path):
    managed_components_path = tmp_path / 'managed_components'
    managed_components_path.mkdir()

    example_cmp_path = managed_components_path / 'example__cmp'
    example_cmp_path.mkdir()
    example_cmp_hash = example_cmp_path / HASH_FILENAME
    example_cmp_hash.write_text('e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')

    mag3110_path = managed_components_path / 'mag3110'
    mag3110_path.mkdir()
    mag3110_hash = mag3110_path / HASH_FILENAME
    mag3110_hash.write_text('e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')

    return str(managed_components_path)


@pytest.fixture(scope='session')
def fixtures_path():
    return os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        'fixtures',
    )


@pytest.fixture(scope='session')
def pre_release_component_path(fixtures_path):
    return os.path.join(
        fixtures_path,
        'components',
        'pre',
    )


@pytest.fixture(scope='session')
def release_component_path(fixtures_path):
    return os.path.join(
        fixtures_path,
        'components',
        'cmp',
    )


@pytest.fixture(scope='session')
def example_component_path(fixtures_path):
    return os.path.join(
        fixtures_path,
        'components',
        'cmp_for_examples',
    )


@pytest.fixture()
def mock_registry_without_token(monkeypatch):
    monkeypatch.setenv('IDF_COMPONENT_REGISTRY_URL', 'http://localhost:5000')


@pytest.fixture()
def mock_registry(mock_registry_without_token, monkeypatch):
    monkeypatch.setenv(
        'IDF_COMPONENT_API_TOKEN',
        'L1nSp1bkNJzi4B-gZ0sIFJi329g69HbQc_JWM8BtfYz-XPM59bzvZeC8jrot-2CZ',
    )


@pytest.fixture
def mock_token_information():
    with requests_mock.Mocker() as m:
        m.get(
            'http://localhost:5000/api/tokens/current',
            json={
                'id': '123',
                'description': 'test token',
                'created_at': '2022-01-01T00:00:00Z',
                'expires_at': None,
                'scope': 'user',
                'access_token_prefix': 'abc123',
            },
        )
        yield m


@pytest.fixture
def hash_component(fixtures_path):
    def inner(id):
        return os.path.join(
            fixtures_path,
            'hash_examples',
            f'component_{id}',
        )

    return inner
