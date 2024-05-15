# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import json
import os

import pytest

from idf_component_tools.config import (
    ConfigError,
    ConfigManager,
    ServiceProfileItem,
)
from idf_component_tools.registry.service_details import (
    get_registry_url,
    get_storage_urls,
)


def test_config_validation():
    # Expect no errors
    ConfigManager.validate({})

    # Assert non-empty object
    assert ConfigManager.validate({
        'profiles': {
            'default': {
                'registry_url': 'default',
            },
            'in_office': {
                'registry_url': 'http://api.localserver.local:5000/',
                'api_token': 'asdf',
                'default_namespace': 'asdf',
            },
        }
    })

    with pytest.raises(ConfigError):
        ConfigManager.validate('asdf')

    with pytest.raises(ConfigError):
        ConfigManager.validate({
            'profiles': {
                'in_office': {'registry_url': 'pptp://api.localserver.local:5000/'},
            }
        })


def test_config_manager_validation(fixtures_path):
    manager = ConfigManager(
        path=os.path.join(fixtures_path, 'config', 'invalid_schema', 'idf_component_manager.yml')
    )

    with pytest.raises(ConfigError):
        manager.load()


def test_config_empty_profile_validation():
    config = ConfigManager.validate({'profiles': {'emptyprofile': None}})
    assert config.profiles['emptyprofile'] is None


def test_load_config(tmp_path):
    config_path = str(tmp_path / 'idf_component_manager.yml')
    config = ConfigManager.validate({
        'profiles': {
            'default': {
                'registry_url': 'default',
            },
            'in_office': {
                'registry_url': 'http://api.localserver.local:5000/',
                'api_token': 'asdf',
                'default_namespace': 'asdf',
            },
        },
        # It's ok to have unknown keys in the config
        'settings': {'abc': 1},
    })

    # Use json representation to compare equality of nested dictionaries
    config_json = json.dumps(config.model_dump(), indent=2)

    manager = ConfigManager(path=config_path)
    # save to file
    manager.dump(config)

    with open(config_path, encoding='utf-8') as file:
        assert file.readline().startswith('profiles:')

    # load from file
    loaded_config = manager.load()

    assert loaded_config.profiles['in_office'].default_namespace == 'asdf'
    assert config_json == json.dumps(loaded_config.model_dump(), indent=2)


def test_config_dump(tmp_path):
    config_path = str(tmp_path / 'idf_component_manager.yml')
    config = ConfigManager.validate({
        'profiles': {
            'default': {
                'registry_url': 'default',
            },
        }
    })
    config.profiles['in_office'] = ServiceProfileItem(
        registry_url='http://api.localserver.local:5000/'
    )

    ConfigManager(path=config_path).dump(config)

    loaded_config = ConfigManager(path=config_path).load()
    assert loaded_config.profiles['in_office'].registry_url == 'http://api.localserver.local:5000/'


def test_component_registry_url_storage_env(monkeypatch):
    monkeypatch.setenv('IDF_COMPONENT_STORAGE_URL', 'https://storage.com/')
    assert ['https://storage.com/'] == get_storage_urls()


def test_component_registry_url_multiple_storage_env(monkeypatch):
    monkeypatch.setenv('IDF_COMPONENT_STORAGE_URL', 'https://storage.com/;https://test.com/')
    assert ['https://storage.com/', 'https://test.com/'] == get_storage_urls()


def test_component_registry_url_registry_api_env(monkeypatch):
    monkeypatch.setenv('DEFAULT_COMPONENT_SERVICE_URL', 'https://registry.com/api/')

    assert 'https://registry.com/api/' == get_registry_url()


def test_component_registry_url_registry_env(monkeypatch):
    monkeypatch.setenv('IDF_COMPONENT_REGISTRY_URL', 'https://registry.com/')
    assert 'https://registry.com/' == get_registry_url()


@pytest.mark.parametrize(
    'profile,registry_url,storage_urls',
    [
        (
            {},
            'https://components.espressif.com/',
            [],
        ),
        (
            None,
            'https://components.espressif.com/',
            [],
        ),
        (
            {'registry_url': 'default'},
            'https://components.espressif.com/',
            [],
        ),
        (
            {'registry_url': 'default', 'storage_url': 'default'},
            'https://components.espressif.com/',
            ['https://components-file.espressif.com/'],
        ),
        (
            {'storage_url': 'default'},
            'https://components.espressif.com/',
            ['https://components-file.espressif.com/'],
        ),
        (
            {'registry_url': 'http://example.com'},
            'http://example.com/',
            [],
        ),
        (
            {'storage_url': 'http://example.com/'},
            'https://components.espressif.com/',
            ['http://example.com/'],
        ),
        (
            {'registry_url': 'http://example.com', 'storage_url': 'http://example.com'},
            'http://example.com/',
            ['http://example.com/'],
        ),
        (
            {'registry_url': None, 'storage_url': ['http://example.com', 'https://test.com']},
            'https://components.espressif.com/',
            ['http://example.com/', 'https://test.com/'],
        ),
    ],
)
def test_component_registry_url_profile(profile, registry_url, storage_urls):
    profile = ServiceProfileItem(**profile) if profile else None

    assert get_registry_url(profile) == registry_url
    assert get_storage_urls(profile) == storage_urls
