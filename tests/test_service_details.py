# SPDX-FileCopyrightText: 2022 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import json
import os

from pytest import fixture, raises

from idf_component_manager.service_details import NoSuchProfile, get_namespace, get_profile, get_token, service_details
from idf_component_tools.config import ConfigManager
from idf_component_tools.errors import FatalError


@fixture()
def service_config(tmp_path):
    return ConfigManager(path=str(tmp_path)).load().profiles.get('default', {})


@fixture()
def config_path(tmp_path):
    config_path = os.path.join(str(tmp_path), 'idf_component_manager.yml')
    with open(config_path, 'w+') as f:
        f.write(
            json.dumps(
                {
                    'profiles': {
                        'test': {
                            'url': 'https://example.com/',
                            'default_namespace': 'espressif',
                            'api_token': 'token'
                        }
                    }
                }))
    return config_path


class TestServiceDetails(object):
    def test_get_namespace_without_namespace(self, service_config):
        with raises(FatalError, match='Failed to get namespace*'):
            get_namespace(service_config)

    def test_get_namespace_with_namespace(self, service_config):
        namespace = get_namespace(service_config, 'example')
        assert namespace == 'example'

    def test_get_token(self, service_config):
        with raises(FatalError, match='Failed to get API Token*'):
            get_token(service_config)

    def test_get_profile_success(self, config_path):
        profile = get_profile(config_path, 'test')
        assert profile['url'] == 'https://example.com/'
        assert profile['default_namespace'] == 'espressif'
        assert profile['api_token'] == 'token'

    def test_get_profile_not_exist(self, config_path):
        assert get_profile(config_path, 'not_test') == {}

    def test_service_details_success(self, config_path):
        client, namespace = service_details(service_profile='test', namespace='test', config_path=config_path)
        assert client.base_url == 'https://example.com/'
        assert namespace == 'test'

    def test_service_details_namespace_not_exist(self):
        with raises(NoSuchProfile):
            service_details(service_profile='not_exists')

    def test_service_details_without_namespace(self, tmp_path):
        with raises(FatalError, match='Failed to get namespace*'):
            service_details(config_path=str(tmp_path))

    def test_service_details_without_token(self, tmp_path):
        with raises(FatalError, match='Failed to get API Token*'):
            service_details(config_path=str(tmp_path), namespace='test')

    def test_service_details_without_profile(self, tmp_path):
        with raises(NoSuchProfile, match='"test" didn\'t find*'):
            service_details(config_path=str(tmp_path), service_profile='test', namespace='test')
