# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import json
import os
from io import open

from pytest import mark, raises

from idf_component_tools.config import (
    Config,
    ConfigError,
    ConfigManager,
    component_registry_url,
    get_api_url,
)


def test_config_validation():
    # Expect no errors
    Config({}).validate()

    # Assert non-empty object
    assert Config(
        {
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
        }
    ).validate()

    with raises(ConfigError):
        Config('asdf').validate()

    with raises(ConfigError):
        Config(
            {
                'profiles': {
                    'in_office': {'registry_url': 'pptp://api.localserver.local:5000/'},
                }
            }
        ).validate()


def test_config_manager_validation(fixtures_path):
    manager = ConfigManager(
        path=os.path.join(fixtures_path, 'config', 'invalid_schema', 'idf_component_manager.yml')
    )

    with raises(ConfigError):
        manager.load()


def test_config_empty_profile_validation():
    config = Config({'profiles': {'emptyprofile': None}}).validate()
    assert config.profiles['emptyprofile'] is None


def test_load_config(tmp_path):
    config_path = str(tmp_path / 'idf_component_manager.yml')
    config = Config(
        {
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
        }
    )

    # Use json representation to compare equality of nested dictionaries
    config_json = json.dumps(dict(config), sort_keys=True, indent=2)

    manager = ConfigManager(path=config_path)
    # save to file
    manager.dump(config)

    with open(config_path, mode='r', encoding='utf-8') as file:
        assert file.readline().startswith('profiles:')

    # load from file
    loaded_config = manager.load()

    assert loaded_config.profiles['in_office']['default_namespace'] == 'asdf'
    assert config_json == json.dumps(dict(loaded_config), sort_keys=True, indent=2)


def test_config_dump(tmp_path):
    config_path = str(tmp_path / 'idf_component_manager.yml')
    config = Config(
        {
            'profiles': {
                'default': {
                    'registry_url': 'default',
                },
            }
        }
    )
    config.profiles.setdefault('in_office', {})[
        'registry_url'
    ] = 'http://api.localserver.local:5000/'

    ConfigManager(path=config_path).dump(config)

    loaded_config = ConfigManager(path=config_path).load()
    assert (
        loaded_config.profiles['in_office']['registry_url'] == 'http://api.localserver.local:5000/'
    )


def test_component_registry_url_storage_env(monkeypatch):
    monkeypatch.setenv('IDF_COMPONENT_STORAGE_URL', 'https://storage.com/')
    assert (None, ['https://storage.com/']) == component_registry_url()


def test_component_registry_url_multiple_storage_env(monkeypatch):
    monkeypatch.setenv('IDF_COMPONENT_STORAGE_URL', 'https://storage.com/;https://test.com/')
    assert (None, ['https://storage.com/', 'https://test.com/']) == component_registry_url()


def test_component_registry_url_registry_api_env(monkeypatch):
    monkeypatch.setenv('DEFAULT_COMPONENT_SERVICE_URL', 'https://registry.com/api/')
    assert ('https://registry.com/api/', None) == component_registry_url()


def test_component_registry_url_registry_env(monkeypatch):
    monkeypatch.setenv('IDF_COMPONENT_REGISTRY_URL', 'https://registry.com/')
    assert ('https://registry.com/api/', None) == component_registry_url()


@mark.parametrize(
    ('profile', 'urls'),
    [
        ({}, ('https://components.espressif.com/api/', ['https://components-file.espressif.com/'])),
        (
            None,
            ('https://components.espressif.com/api/', ['https://components-file.espressif.com/']),
        ),
        (
            {'registry_url': 'default'},
            ('https://components.espressif.com/api/', ['https://components-file.espressif.com/']),
        ),
        (
            {'registry_url': 'default', 'storage_url': 'default'},
            ('https://components.espressif.com/api/', ['https://components-file.espressif.com/']),
        ),
        (
            {'storage_url': 'default'},
            ('https://components.espressif.com/api/', ['https://components-file.espressif.com/']),
        ),
        (
            {'registry_url': 'http://example.com'},
            ('http://example.com/api/', None),
        ),
        (
            {'storage_url': 'http://example.com/'},
            (None, ['http://example.com/']),
        ),
        (
            {'registry_url': 'http://example.com', 'storage_url': 'http://example.com'},
            ('http://example.com/api/', ['http://example.com']),
        ),
        (
            {'registry_url': None, 'storage_url': ['http://example.com', 'https://test.com']},
            (None, ['http://example.com', 'https://test.com']),
        ),
    ],
)
def test_component_registry_url_profile(profile, urls):
    assert component_registry_url(profile) == urls


@mark.parametrize(
    ['url', 'res'],
    [
        ('http://example.com', 'http://example.com/api/'),
        ('http://example.com/', 'http://example.com/api/'),
        ('http://example.com/api', 'http://example.com/api/'),
        ('http://example.com/api/', 'http://example.com/api/'),
    ],
)
def test_get_api_url(url, res):
    assert get_api_url(url) == res
