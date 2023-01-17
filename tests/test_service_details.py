# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import json
import os

from pytest import deprecated_call, fixture, raises, warns

from idf_component_manager.service_details import NoSuchProfile, get_namespace, get_profile, get_token, service_details
from idf_component_tools.config import Config, ConfigManager
from idf_component_tools.errors import FatalError


@fixture()
def service_config(tmp_path):
    return Config({}).validate().profiles.get('default', {})


@fixture()
def config_path(tmp_path):
    config_path = os.path.join(str(tmp_path), 'idf_component_manager.yml')
    with open(config_path, 'w+') as f:
        f.write(
            json.dumps(
                {
                    'profiles': {
                        'test': {
                            'registry_url': 'https://example.com/',
                            'default_namespace': 'test',
                            'api_token': 'token'
                        }
                    }
                }))
    return config_path


def test_get_namespace_from_config():
    service_config = {
        'default_namespace': 'test',
    }
    assert get_namespace(service_config) == 'test'


def test_get_namespace_with_namespace(service_config):
    namespace = get_namespace(service_config, 'example')
    assert namespace == 'example'


def test_get_namespace_default(service_config):
    namespace = get_namespace(service_config, None)
    assert namespace == 'espressif'


def test_get_token_fails(service_config):
    with raises(FatalError, match='Failed to get API Token*'):
        get_token(service_config)


def test_get_token_env(service_config, monkeypatch):
    monkeypatch.setenv('IDF_COMPONENT_API_TOKEN', 'some_token')
    assert get_token(service_config) == 'some_token'


def test_get_token_profile(config_path, monkeypatch):
    profile = ConfigManager(path=config_path).load().profiles['test']
    assert get_token(profile) == 'token'


def test_get_token_allow_none(service_config):
    assert get_token(service_config, token_required=False) is None


def test_get_profile_success(config_path):
    profile = get_profile(config_path, 'test')
    assert profile['registry_url'] == 'https://example.com/'
    assert profile['default_namespace'] == 'test'
    assert profile['api_token'] == 'token'


def test_get_profile_env_dep(config_path, monkeypatch):
    monkeypatch.setenv('IDF_COMPONENT_SERVICE_PROFILE', 'test')
    with deprecated_call():
        assert get_profile(config_path)['default_namespace'] == 'test'


def test_get_profile_env(config_path, monkeypatch):
    monkeypatch.setenv('IDF_COMPONENT_REGISTRY_PROFILE', 'test')
    assert get_profile(config_path)['default_namespace'] == 'test'


def test_get_profile_env_both(config_path, monkeypatch):
    monkeypatch.setenv('IDF_COMPONENT_SERVICE_PROFILE', 'test')
    monkeypatch.setenv('IDF_COMPONENT_REGISTRY_PROFILE', 'test')
    with warns(UserWarning, match='IDF_COMPONENT_SERVICE_PROFILE and IDF_COMPONENT_REGISTRY_PROFILE'):
        assert get_profile(config_path)['default_namespace'] == 'test'


def test_get_profile_not_exist(config_path):
    assert get_profile(config_path, 'not_test') == {}


def test_service_details_success(config_path):
    client, namespace = service_details(service_profile='test', namespace='test', config_path=config_path)
    assert client.base_url == 'https://example.com/api/'
    assert namespace == 'test'


def test_service_details_namespace_not_exist(tmp_path):
    with raises(NoSuchProfile):
        service_details(config_path=str(tmp_path), service_profile='not_exists')


def test_service_details_without_token(tmp_path):
    with raises(FatalError, match='Failed to get API Token*'):
        service_details(config_path=str(tmp_path), namespace='test')


def test_service_details_without_profile(tmp_path):
    with raises(NoSuchProfile, match='Profile "test" not found*'):
        service_details(config_path=str(tmp_path), service_profile='test', namespace='test')
