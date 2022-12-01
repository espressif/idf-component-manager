# SPDX-FileCopyrightText: 2022 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os

import pytest
import vcr

from idf_component_manager import version
from idf_component_tools.api_client import APIClient, join_url, user_agent
from idf_component_tools.api_client_errors import NoRegistrySet
from idf_component_tools.config import component_registry_url


@pytest.fixture
def base_url():
    return 'http://localhost:5000'


class TestAPIClient(object):
    def test_join_url(self):
        tests = [
            {
                'in': ['http://', 'test.com', 'asdfasdf'],
                'out': 'http://test.com/asdfasdf',
            },
            {
                'in': ['https://test.com:4323/api', 'a/a'],
                'out': 'https://test.com:4323/api/a/a',
            },
            {
                'in': ['https://test.com:4323/api/', 'a/a/'],
                'out': 'https://test.com:4323/api/a/a',
            },
            {
                'in': ['', 'a/a/'],
                'out': '/a/a'
            },
        ]

        for test in tests:
            assert join_url(*test['in']) == test['out']

    @vcr.use_cassette('tests/fixtures/vcr_cassettes/test_component_versions.yaml')
    def test_version(self, base_url):
        client = APIClient(base_url=base_url)

        # Also check case normalisation
        component = client.versions(component_name='Test/Cmp', spec='>=1.0.0')

        assert component.name == 'test/cmp'
        assert len(list(component.versions)) == 2

    @vcr.use_cassette('tests/fixtures/vcr_cassettes/test_component_details.yaml')
    def test_component(self, base_url):
        storage_name = 'http://localhost:9000/test-public/'

        client = APIClient(base_url=base_url)

        # Also check case normalisation
        manifest = client.component(component_name='tesT/CMP')

        assert manifest.name == 'test/cmp'
        assert str(manifest.version) == '1.0.1'
        assert manifest.download_url.startswith(storage_name)
        assert manifest.documents['readme'].startswith(storage_name)
        assert manifest.examples[0]['url'].startswith(storage_name)
        assert manifest.license['url'].startswith(storage_name)

    def test_user_agent(self, base_url):
        ua = user_agent()
        assert str(version) in ua

    @vcr.use_cassette(
        'tests/fixtures/vcr_cassettes/test_api_cache.yaml',
        record_mode='none',
    )
    def test_api_cache(self, base_url, monkeypatch):
        """
        This test is checking api caching with using the same requests 2 times.
        In test_api_cache.yaml we have just one request, so if test is passed,
        one request was from the cassette, and one from the cache.
        WARNING: Don't overwrite the test_api_cache.yaml file. It can break the test.
        """
        monkeypatch.setenv('IDF_COMPONENT_API_CACHE_EXPIRATION_MINUTES', '180')
        client = APIClient(base_url=base_url)

        client.component(component_name='test/cmp')
        client.component(component_name='test/cmp')

    @vcr.use_cassette('tests/fixtures/vcr_cassettes/test_api_information.yaml')
    def test_api_information(self, base_url):
        client = APIClient(base_url=base_url)

        assert client.storage_url == 'http://localhost:9000/test-public'

    def test_file_adapter(self, base_url, fixtures_path):
        storage_url = '{}{}'.format('file://', fixtures_path)
        client = APIClient(base_url, storage_url=storage_url)

        assert client.component(component_name='example/cmp').download_url == os.path.join(
            storage_url, '86f07b70-bb83-45f0-99c7-a10f82781f5a.tgz')

    def test_no_registry_url_error(self, monkeypatch):
        monkeypatch.setenv('IDF_COMPONENT_STORAGE_URL', 'http://localhost:9000/test-public')

        registry_url, storage_url = component_registry_url()
        client = APIClient(base_url=registry_url, storage_url=storage_url, auth_token='test')
        with pytest.raises(NoRegistrySet):
            client.upload_version(component_name='example/cmp')

    @vcr.use_cassette('tests/fixtures/vcr_cassettes/test_no_registry_url_use_static.yaml')
    def test_no_registry_url_use_static(self, monkeypatch):
        monkeypatch.setenv('IDF_COMPONENT_STORAGE_URL', 'http://localhost:9000/test-public')

        registry_url, storage_url = component_registry_url()
        client = APIClient(base_url=registry_url, storage_url=storage_url, auth_token='test')
        client.component(component_name='espressif/cmp')  # no errors
