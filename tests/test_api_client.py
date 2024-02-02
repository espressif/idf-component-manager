# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os
import sys
from ssl import SSLEOFError

import pytest
import vcr
from requests import Response

from idf_component_manager import version
from idf_component_tools.config import component_registry_url
from idf_component_tools.constants import IDF_COMPONENT_REGISTRY_URL, IDF_COMPONENT_STORAGE_URL
from idf_component_tools.registry.api_client import APIClient
from idf_component_tools.registry.api_client_errors import APIClientError, NoRegistrySet
from idf_component_tools.registry.base_client import env_cache_time, user_agent
from idf_component_tools.registry.multi_storage_client import MultiStorageClient
from idf_component_tools.registry.request_processor import join_url
from idf_component_tools.registry.storage_client import StorageClient
from idf_component_tools.semver import Version


@pytest.fixture
def base_url():
    return 'http://localhost:5000/api'


@pytest.fixture
def storage_url():
    return 'http://localhost:9000/test-public'


def response_413(*_, **__):
    response = Response()
    response.status_code = 413
    return response


def raise_SSLEOFError(*_, **__):
    raise SSLEOFError()


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
            {'in': ['', 'a/a/'], 'out': '/a/a'},
        ]

        for test in tests:
            assert join_url(*test['in']) == test['out']

    @vcr.use_cassette('tests/fixtures/vcr_cassettes/test_component_versions.yaml')
    def test_version(self, storage_url):
        client = StorageClient(storage_url=storage_url)

        # Also check case normalisation
        component = client.versions(component_name='Test/Cmp', spec='>=1.0.0')

        assert component.name == 'test/cmp'
        assert len(list(component.versions)) == 2

    @vcr.use_cassette('tests/fixtures/vcr_cassettes/test_component_details.yaml')
    def test_component(self, storage_url):
        client = StorageClient(storage_url=storage_url)

        # Also check case normalisation
        manifest = client.component(component_name='tesT/CMP')

        assert manifest.name == 'test/cmp'
        assert str(manifest.version) == '1.0.1'
        assert manifest.download_url.startswith(storage_url)
        assert manifest.documents['readme'].startswith(storage_url)
        assert manifest.examples[0]['url'].startswith(storage_url)
        assert manifest.license_url.startswith(storage_url)

    def test_user_agent(self, base_url):
        ua = user_agent()
        assert str(version) in ua

    def test_env_cache_time_empty(self, monkeypatch):
        monkeypatch.setenv('IDF_COMPONENT_API_CACHE_EXPIRATION_MINUTES', '')
        assert env_cache_time() == 0

    def test_env_cache_time_env_var(self, monkeypatch):
        monkeypatch.setenv('IDF_COMPONENT_API_CACHE_EXPIRATION_MINUTES', '10')
        assert env_cache_time() == 10

    def test_env_cache_time(self, monkeypatch):
        monkeypatch.delenv('IDF_COMPONENT_API_CACHE_EXPIRATION_MINUTES')
        assert env_cache_time() == 0

    @vcr.use_cassette(
        'tests/fixtures/vcr_cassettes/test_api_cache.yaml',
        record_mode='none',
    )
    def test_api_cache(self, storage_url, monkeypatch, tmp_path):
        """
        This test is checking api caching with using the same requests 2 times.
        In test_api_cache.yaml we have just one request, so if test is passed,
        one request was from the cassette, and one from the cache.
        WARNING: Don't overwrite the test_api_cache.yaml file. It can break the test.
        """

        # vcrpy 2.0.1 compatible with py3.4 doesn't play nice with caching
        # It was manually checked that cache itself works
        if sys.version_info[0] == 3 and sys.version_info[1] == 4:
            return

        monkeypatch.setenv('IDF_COMPONENT_API_CACHE_EXPIRATION_MINUTES', '180')
        monkeypatch.setenv('IDF_COMPONENT_CACHE_PATH', str(tmp_path))
        client = StorageClient(storage_url=storage_url)

        client.component(component_name='test/cmp')
        client.component(component_name='test/cmp')

    @vcr.use_cassette('tests/fixtures/vcr_cassettes/test_api_information.yaml')
    def test_api_information(self, base_url):
        client = APIClient(base_url=base_url)
        information = client.api_information()
        assert information['components_base_url'] == 'http://localhost:9000/test-public'

    def test_file_adapter(self, fixtures_path):
        storage_url = '{}{}'.format('file://', fixtures_path)
        client = StorageClient(storage_url=storage_url)

        assert client.component(component_name='example/cmp').download_url == os.path.join(
            storage_url, '5390a837-5bc7-4564-b747-3adb22ad55f8.tgz'
        )

    def test_no_registry_url_error(self, monkeypatch, tmp_path):
        monkeypatch.setenv('IDF_COMPONENT_STORAGE_URL', 'http://localhost:9000/test-public')

        registry_url, _ = component_registry_url()
        client = APIClient(base_url=registry_url, auth_token='test')

        file_path = str(tmp_path / 'cmp.tgz')
        with open(file_path, 'w+') as f:
            f.write('a')

        with pytest.raises(NoRegistrySet):
            client.upload_version(component_name='example/cmp', file_path=file_path)

    def test_env_var_for_upload_empty(self, monkeypatch):
        monkeypatch.setenv('IDF_COMPONENT_STORAGE_URL', '')
        monkeypatch.setenv('IDF_COMPONENT_REGISTRY_URL', '')
        monkeypatch.setenv('IDF_COMPONENT_API_TOKEN', '')

        registry_url, storage_urls = component_registry_url()
        assert registry_url == IDF_COMPONENT_REGISTRY_URL + 'api/'
        assert storage_urls == [IDF_COMPONENT_STORAGE_URL]

    @vcr.use_cassette('tests/fixtures/vcr_cassettes/test_no_registry_url_use_static.yaml')
    def test_no_registry_url_use_static(self, monkeypatch):
        monkeypatch.setenv('IDF_COMPONENT_STORAGE_URL', 'http://localhost:9000/test-public')

        registry_url, storage_urls = component_registry_url()
        client = MultiStorageClient(storage_urls=storage_urls)
        client.component(component_name='espressif/cmp')  # no errors

    @vcr.use_cassette('tests/fixtures/vcr_cassettes/test_filter_yanked_version.yaml')
    @pytest.mark.parametrize('version', ['=1.1.0', '1.1.0', '==1.1.0,==1.1.0'])
    def test_only_yanked_version_warning(self, storage_url, version):
        client = StorageClient(storage_url=storage_url)

        with pytest.warns(UserWarning, match='component you have selected has been yanked'):
            client.component(component_name='example/cmp_yanked', version=version)

    @vcr.use_cassette('tests/fixtures/vcr_cassettes/test_filter_yanked_version.yaml')
    @pytest.mark.parametrize(
        'spec',
        [
            '>1.0.0',
            '^1.0.0',
            '1.*.*',
            '*',
            None,
        ],
    )
    def test_filter_yanked_version_for_component(self, storage_url, spec):
        client = StorageClient(storage_url=storage_url)
        result = client.component(component_name='example/cmp_yanked', version=spec)

        assert result.version == '1.0.1'

    @vcr.use_cassette('tests/fixtures/vcr_cassettes/test_filter_yanked_version.yaml')
    @pytest.mark.parametrize(
        'spec',
        [
            '>1.0.0',
            '^1.0.0',
            '1.*.*',
            '*',
            None,
        ],
    )
    def test_filter_yanked_version_for_component_versions(self, storage_url, spec):
        client = StorageClient(storage_url=storage_url)

        result = client.versions(component_name='example/cmp_yanked', spec=spec)
        assert result.versions[0].semver == Version('1.0.1')

    def test_token_information(self, base_url, mock_registry, mock_token_information):
        client = APIClient(base_url=base_url, auth_token='test')
        response = client.token_information()

        for k, v in {
            'access_token_prefix': 'abc123',
            'scope': 'user',
            'description': 'test token',
            'expires_at': None,
            'created_at': '2022-01-01T00:00:00Z',
            'id': '123',
        }.items():
            assert response[k] == v

    @vcr.use_cassette('tests/fixtures/vcr_cassettes/test_token_information_with_exception.yaml')
    def test_token_information_with_exception(self, base_url):
        client = APIClient(base_url=base_url)
        with pytest.raises(Exception):
            client.token_information()

    @vcr.use_cassette('tests/fixtures/vcr_cassettes/test_version_multiple_storages.yaml')
    def test_version_multiple_storages(self, fixtures_path):
        storage_file_path = 'file://{}/'.format(fixtures_path)
        storage_urls = [storage_file_path, 'https://components-file.espressif.com']
        client = MultiStorageClient(storage_urls=storage_urls)
        result = client.versions(component_name='example/cmp')

        assert result.versions
        assert result.storage_url == storage_file_path

        result = client.versions('espressif/mdns')

        assert result.versions
        assert result.storage_url == 'https://components-file.espressif.com'

    def test_upload_component_returns_413_status(self, tmp_path, base_url, monkeypatch):
        monkeypatch.setattr(
            'idf_component_tools.registry.request_processor.make_request', response_413
        )
        client = APIClient(
            base_url=base_url,
            auth_token='test',
        )

        file_path = str(tmp_path / 'cmp.tgz')
        with open(file_path, 'w+') as f:
            f.write('a')

        with pytest.raises(APIClientError) as e:
            client.upload_version(
                component_name='kumekay/cmp',
                file_path=file_path,
            )
        assert str(e.value).startswith('The component archive exceeds the maximum allowed size')

    def test_upload_component_SSLEOFError(self, tmp_path, base_url, monkeypatch):
        monkeypatch.setattr(
            'idf_component_tools.registry.request_processor.make_request', raise_SSLEOFError
        )
        client = APIClient(
            base_url=base_url,
            auth_token='test',
        )

        file_path = str(tmp_path / 'cmp.tgz')
        with open(file_path, 'w+') as f:
            f.write('a')

        with pytest.raises(APIClientError) as e:
            client.upload_version(
                component_name='kumekay/cmp',
                file_path=file_path,
            )
        assert str(e.value).startswith('The component archive exceeds the maximum allowed size')
