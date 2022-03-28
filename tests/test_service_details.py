import json
import os

from pytest import raises

from idf_component_manager.service_details import NoSuchProfile, service_details
from idf_component_tools.errors import FatalError


class TestServiceDetails(object):
    def test_service_details_without_namespace(self):
        with raises(FatalError, match='Namespace*'):
            service_details()

    def test_service_details_without_token(self):
        with raises(FatalError, match='API token*'):
            service_details(namespace='test')

    def test_service_details_without_profile(self):
        with raises(NoSuchProfile, match='"test" didn\'t find*'):
            service_details(service_profile='test', namespace='test')

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
