# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import json
import os

from pytest import fixture, raises, warns

from idf_component_tools.config import Config
from idf_component_tools.constants import DEFAULT_NAMESPACE
from idf_component_tools.messages import UserDeprecationWarning
from idf_component_tools.registry.client_errors import APIClientError
from idf_component_tools.registry.service_details import (
    NoSuchProfile,
    get_api_client,
    get_profile,
    get_storage_client,
)


@fixture()
def service_config(tmp_path):
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


def test_get_namespace_with_namespace():
    assert get_api_client(namespace='example').default_namespace == 'example'


def test_get_namespace_default():
    assert get_storage_client(namespace=None).default_namespace == DEFAULT_NAMESPACE


def test_get_namespace_from_profile(
    config_path,
):
    api_client = get_api_client(profile_name='test', config_path=config_path)
    assert api_client.default_namespace == 'test'


def test_get_token_env(monkeypatch):
    monkeypatch.setenv('IDF_COMPONENT_API_TOKEN', 'some_token')

    assert get_api_client().api_token == 'some_token'


def test_empty_env_profile(monkeypatch):
    monkeypatch.setenv('IDF_COMPONENT_PROFILE', '')
    with raises(
        NoSuchProfile,
        match='Profile "not_exists" not found in the idf_component_manager.yml config file',
    ):
        get_api_client(profile_name='not_exists')


def test_get_token_profile(config_path, monkeypatch):
    api_client = get_api_client(profile_name='test', config_path=config_path)
    assert api_client.api_token == 'token'


def test_get_profile_success(config_path):
    profile = get_profile('test', config_path)
    assert profile.registry_url == 'https://example.com/'
    assert profile.default_namespace == 'test'
    assert profile.api_token == 'token'


def test_get_service_profile_env_dep(config_path, monkeypatch):
    monkeypatch.setenv('IDF_COMPONENT_SERVICE_PROFILE', 'test')
    with warns(UserDeprecationWarning):
        assert get_profile(None, config_path=config_path).default_namespace == 'test'


def test_get_registry_profile_env_dep(config_path, monkeypatch):
    monkeypatch.setenv('IDF_COMPONENT_REGISTRY_PROFILE', 'test2')
    with warns(UserDeprecationWarning):
        assert get_profile(None, config_path=config_path).default_namespace == 'test2'


def test_get_profile_env(config_path, monkeypatch):
    monkeypatch.setenv('IDF_COMPONENT_PROFILE', 'test3')
    assert get_profile(None, config_path=config_path).default_namespace == 'test3'


def test_get_profile_not_exist(config_path):
    assert get_profile('not_exists', config_path) is None


def test_get_profile_with_default_name(config_path):
    profile = get_profile('default', config_path)
    assert profile.registry_url == 'https://default.com/'
    assert profile.default_namespace == 'default_ns'
    assert profile.api_token is None


def test_service_details_success(config_path):
    client = get_storage_client(profile_name='test', namespace='test', config_path=config_path)
    assert client.registry_url == 'https://example.com/'
    assert client.default_namespace == 'test'


def test_service_details_namespace_not_exist(tmp_path):
    with raises(NoSuchProfile):
        get_storage_client(config_path=str(tmp_path), profile_name='not_exists')


def test_service_details_without_token(tmp_path):
    client = get_api_client(config_path=str(tmp_path), namespace='test')

    with raises(APIClientError, match='API token is required'):
        client.upload_version('file', 'component', '1.0.0')


def test_service_details_without_profile(tmp_path):
    with raises(NoSuchProfile, match='Profile "test" not found*'):
        get_storage_client(config_path=str(tmp_path), profile_name='test', namespace='test')


def test_service_details_with_empty_profile(config_path):
    client = get_api_client(config_path=config_path, profile_name='emptyprofile')
    with raises(APIClientError, match='API token is required'):
        client.upload_version('file', 'component', '1.0.0')


def test_get_component_registry_url_with_profile(monkeypatch, config_path):
    monkeypatch.setenv('IDF_COMPONENT_PROFILE', 'test')

    client = get_storage_client(config_path=config_path)

    assert client.registry_url == 'https://example.com/'
    assert client.storage_urls == []
