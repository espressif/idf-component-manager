# SPDX-FileCopyrightText: 2022-2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import json
import os

import pytest
from jsonref import requests
from pytest import fixture, raises, warns

from idf_component_tools.config import Config, ConfigError, get_profile
from idf_component_tools.constants import (
    DEFAULT_NAMESPACE,
    IDF_COMPONENT_STAGING_REGISTRY_URL,
)
from idf_component_tools.errors import NoSuchProfile
from idf_component_tools.messages import UserDeprecationWarning
from idf_component_tools.registry.client_errors import APIClientError
from idf_component_tools.registry.multi_storage_client import MultiStorageClient
from idf_component_tools.registry.service_details import (
    get_api_client,
    get_storage_client,
)


@fixture()
def service_config():
    return Config().profiles.get('default', {})


@fixture()
def config_path(tmp_path):
    config_path = os.path.join(str(tmp_path), 'idf_component_manager.yml')
    with open(config_path, 'w+') as f:
        f.write(
            json.dumps({
                'profiles': {
                    'default': {
                        'registry_url': 'https://default.com/',
                        'default_namespace': 'default_ns',
                        'api_token': None,
                    },
                    'test': {
                        'registry_url': 'https://example.com/',
                        'default_namespace': 'test',
                        'api_token': 'token',
                    },
                    'test2': {
                        'registry_url': 'https://example2.com/',
                        'default_namespace': 'test2',
                        'api_token': 'token',
                    },
                    'test3': {
                        'registry_url': 'https://example3.com/',
                        'default_namespace': 'test3',
                        'api_token': 'token',
                    },
                    'emptyprofile': None,
                }
            })
        )
    return config_path


class TestGetProfile:
    def test_get_profile_success(self, config_path):
        profile = get_profile('test', config_path)
        assert profile.registry_url == 'https://example.com/'
        assert profile.default_namespace == 'test'
        assert profile.api_token == 'token'

    def test_get_service_profile_env_dep(self, config_path, monkeypatch):
        monkeypatch.setenv('IDF_COMPONENT_SERVICE_PROFILE', 'test')
        with warns(UserDeprecationWarning):
            assert get_profile(None, config_path=config_path).default_namespace == 'test'

    def test_get_registry_profile_env_dep(self, config_path, monkeypatch):
        monkeypatch.setenv('IDF_COMPONENT_REGISTRY_PROFILE', 'test2')
        with warns(UserDeprecationWarning):
            assert get_profile(None, config_path=config_path).default_namespace == 'test2'

    def test_get_profile_env(self, config_path, monkeypatch):
        monkeypatch.setenv('IDF_COMPONENT_PROFILE', 'test3')
        assert get_profile(None, config_path=config_path).default_namespace == 'test3'

    def test_get_profile_not_exist(self, config_path):
        with raises(
            NoSuchProfile,
            match='Profile "not_exists" not found in config file:.+idf_component_manager.yml',
        ):
            assert get_profile('not_exists', config_path)

    def test_get_profile_with_default_name(self, config_path):
        profile = get_profile('default', config_path)
        assert profile.registry_url == 'https://default.com/'
        assert profile.default_namespace == 'default_ns'
        assert profile.api_token is None

    def test_invalid_field_error_message(self, tmp_path):
        config_path = os.path.join(str(tmp_path), 'idf_component_manager.yml')
        with open(config_path, 'w+') as f:
            f.write(
                json.dumps({
                    'profiles': {
                        'default': {
                            'registry_url': 'foo',
                            'storage_url': [
                                'http://test.me',
                                'bar',
                            ],
                            'local_storage_url': 'foo',
                        }
                    }
                })
            )

        with pytest.raises(ConfigError) as e:
            get_profile('default', config_path)
            msgs = str(e).split('\n')
            assert 'Invalid field "profiles:default:registry_url":' in msgs[0]
            assert 'Invalid field "profiles:default:storage_url:[1]":' in msgs[1]
            assert 'Invalid field "profiles:default:local_storage_url":' in msgs[2]


class TestApiClient:
    def test_get_namespace_with_namespace(self):
        assert get_api_client(namespace='example').default_namespace == 'example'

    def test_get_namespace_from_profile(self, config_path):
        api_client = get_api_client(profile_name='test', config_path=config_path)
        assert api_client.default_namespace == 'test'

    def test_get_token_env(self, monkeypatch):
        monkeypatch.setenv('IDF_COMPONENT_API_TOKEN', 'some_token')

        assert get_api_client().api_token == 'some_token'

    def test_empty_env_profile(self, monkeypatch):
        monkeypatch.setenv('IDF_COMPONENT_PROFILE', '')
        with raises(
            NoSuchProfile,
            match='Profile "not_exists" not found in config file:.+idf_component_manager.yml',
        ):
            get_api_client(profile_name='not_exists')

    def test_get_token_profile(self, config_path):
        api_client = get_api_client(profile_name='test', config_path=config_path)
        assert api_client.api_token == 'token'

    def test_service_details_without_token(self, tmp_path):
        client = get_api_client(config_path=str(tmp_path), namespace='test')

        with raises(APIClientError, match='API token is required'):
            client.upload_version('file', 'component', '1.0.0')

    def test_service_details_with_empty_profile(self, config_path):
        client = get_api_client(config_path=config_path, profile_name='emptyprofile')
        with raises(APIClientError, match='API token is required'):
            client.upload_version('file', 'component', '1.0.0')


class TestMultiStorageClient:
    def test_get_namespace_default(self):
        assert get_storage_client().default_namespace == DEFAULT_NAMESPACE

    def test_service_details_success(self, config_path):
        client = get_storage_client(profile_name='test', namespace='test', config_path=config_path)
        assert client.registry_url == 'https://example.com/'
        assert client.default_namespace == 'test'

    def test_service_details_namespace_not_exist(self, tmp_path):
        with raises(NoSuchProfile):
            get_storage_client(config_path=str(tmp_path), profile_name='not_exists')

    def test_service_details_without_profile(self, tmp_path):
        with raises(NoSuchProfile, match='Profile "test" not found*'):
            get_storage_client(config_path=str(tmp_path), profile_name='test', namespace='test')

    def test_get_component_registry_url_with_profile(self, monkeypatch, config_path):
        monkeypatch.setenv('IDF_COMPONENT_PROFILE', 'test')

        client = get_storage_client(config_path=config_path)

        assert client.registry_url == 'https://example.com/'
        assert client.storage_urls == []

    def test_registry_storage_url(self):
        client = get_storage_client(registry_url=IDF_COMPONENT_STAGING_REGISTRY_URL)

        assert (
            client.registry_storage_client.storage_url
            == requests.get(IDF_COMPONENT_STAGING_REGISTRY_URL + '/api').json()[
                'components_base_url'
            ]
        )

    def test_storage_clients_precedence(self):
        client = get_storage_client(
            registry_url=IDF_COMPONENT_STAGING_REGISTRY_URL,
            storage_urls=['https://something.else'],
            local_storage_urls=['file://local1', 'file://local2'],
        )

        storage_clients = list(client.storage_clients)
        assert storage_clients[0].storage_url == 'file://local1'
        assert storage_clients[1].storage_url == 'file://local2'
        assert storage_clients[2].storage_url == 'https://something.else'
        assert (
            storage_clients[3].storage_url
            == requests.get(IDF_COMPONENT_STAGING_REGISTRY_URL + '/api').json()[
                'components_base_url'
            ]
        )

    def test_storage_clients_deduplicate_same_url(self):
        same_storage_url = 'http://localhost:9000/test-public'

        # Create client with same URL in both local and profile storage
        client = MultiStorageClient(
            local_storage_urls=[same_storage_url],
            storage_urls=[same_storage_url],
        )

        storage_clients = list(client.storage_clients)
        storage_urls = [c.storage_url for c in storage_clients]

        assert len(storage_urls) == 1
        assert storage_urls[0] == same_storage_url

    def test_storage_clients_deduplicate_trailing_slash(self):
        url1 = 'http://example.com/storage'
        url2 = 'http://example.com/storage/'

        client = MultiStorageClient(
            storage_urls=[url1],
            local_storage_urls=[url2],  # Same URL with trailing slash
        )

        storage_clients = list(client.storage_clients)
        storage_urls = [c.storage_url for c in storage_clients]

        assert len(storage_urls) == 1
        assert storage_urls[0] == url2

    def test_storage_clients_deduplicate_multiple_profile_urls(self):
        url1 = 'http://example.com/storage'
        url2 = 'http://example.com/storage/'  # Same URL with trailing slash
        url3 = 'http://example.com/other'

        client = MultiStorageClient(storage_urls=[url1, url2, url3])

        storage_clients = list(client.storage_clients)
        storage_urls = [c.storage_url for c in storage_clients]

        assert len(storage_urls) == 2
        assert url1 in storage_urls or url2 in storage_urls
        assert url3 in storage_urls

    def test_storage_clients_preserves_priority_order(self):
        local_url = 'file://local'
        profile_url = 'http://profile'

        client = MultiStorageClient(
            local_storage_urls=[local_url],
            storage_urls=[profile_url],
        )

        storage_clients = list(client.storage_clients)
        storage_urls = [c.storage_url for c in storage_clients]

        assert len(storage_urls) == 2
        assert storage_urls[0] == local_url
        assert storage_urls[1] == profile_url
