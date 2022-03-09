import json
import os

from pytest import raises

from idf_component_manager.service_details import NoSuchProfile, get_namespace, get_profile, get_token, service_details
from idf_component_tools.config import ConfigManager
from idf_component_tools.errors import FatalError


class TestServiceDetails(object):
    def test_get_namespace_without_namespace(self):
        config = ConfigManager().load().profiles.get('default', {})
        with raises(FatalError, match='Failed to get namespace*'):
            get_namespace(config)

    def test_get_namespace_with_namespace(self):
        config = ConfigManager().load().profiles.get('default', {})
        namespace = get_namespace(config, 'example')
        assert namespace == 'example'

    def test_get_token(self):
        config = ConfigManager().load().profiles.get('default', {})
        with raises(FatalError, match='Failed to get API Token*'):
            get_token(config)

    def test_get_profile_success(self, tmp_path):
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
        profile = get_profile(config_path, 'test')
        assert profile['url'] == 'https://example.com/'
        assert profile['default_namespace'] == 'espressif'
        assert profile['api_token'] == 'token'

    def test_get_profile_not_exist(self, tmp_path):
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

        assert get_profile(config_path, 'not_test') == {}

    def test_service_details_namespace_not_exist(self):
        with raises(NoSuchProfile):
            service_details(service_profile='not_exists')

    def test_service_details_success(self, tmp_path):
        with open(os.path.join(str(tmp_path), 'idf_component_manager.yml'), 'w+') as f:
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
        client, namespace = service_details(
            service_profile='test',
            namespace='test',
            config_path=os.path.join(str(tmp_path), 'idf_component_manager.yml'))
        assert client.base_url == 'https://example.com/'
        assert namespace == 'test'
