# SPDX-FileCopyrightText: 2022-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import logging
import os
import typing as t
from ssl import SSLEOFError

import pytest
import requests_mock
from requests import Response

from idf_component_tools import LOGGING_NAMESPACE
from idf_component_tools.__version__ import __version__
from idf_component_tools.config import get_registry_url, get_storage_urls
from idf_component_tools.constants import IDF_COMPONENT_REGISTRY_URL
from idf_component_tools.registry.api_client import APIClient
from idf_component_tools.registry.base_client import user_agent
from idf_component_tools.registry.client_errors import APIClientError
from idf_component_tools.registry.multi_storage_client import MultiStorageClient
from idf_component_tools.registry.request_processor import join_url
from idf_component_tools.registry.storage_client import StorageClient
from idf_component_tools.semver import Version
from tests.network_test_utils import use_vcr_or_real_env


@pytest.fixture
def registry_url():
    return os.getenv('IDF_COMPONENT_REGISTRY_URL') or 'http://localhost:5000'


@pytest.fixture
def storage_url():
    return os.getenv('IDF_COMPONENT_STORAGE_URL') or 'http://localhost:9000/test-public'


def response_413(*_, **__):
    response = Response()
    response.status_code = 413
    return response


def response_403(messages: t.List[str], *_, **__):
    response = Response()
    response.status_code = 403
    response.json = lambda: {'messages': messages}  # type: ignore
    return response


def raise_SSLEOFError(*_, **__):
    raise SSLEOFError()


class TestAPIClient:
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

    @use_vcr_or_real_env('tests/fixtures/vcr_cassettes/test_component_versions.yaml')
    @pytest.mark.network
    def test_version(self, storage_url):
        client = StorageClient(storage_url=storage_url)

        # Also check case normalisation
        component = client.versions(component_name='Test_component_manager/Cmp', spec='>=1.0.0')

        assert component.name == 'test_component_manager/cmp'
        assert len(list(component.versions)) == 3

    @use_vcr_or_real_env('tests/fixtures/vcr_cassettes/test_component_details.yaml')
    @pytest.mark.network
    def test_component(self, storage_url):
        client = StorageClient(storage_url=storage_url)

        # Also check case normalisation
        result = client.component(component_name='test_component_manageR/CMP')

        assert result['name'] == 'test_component_manager/cmp'
        assert result['version'] == '2.0.0-alpha1'
        assert result['docs']['readme'].startswith(storage_url)
        assert result['examples'][0]['url'].startswith(storage_url)
        assert result['license']['url'].startswith(storage_url)

    def test_user_agent(self):
        ua = user_agent()
        assert str(__version__) in ua

    @use_vcr_or_real_env('tests/fixtures/vcr_cassettes/test_api_information.yaml')
    @pytest.mark.network
    def test_api_information(self, registry_url, storage_url):
        client = APIClient(registry_url=registry_url)
        information = client.api_information()
        assert information['components_base_url'] == storage_url

    def test_file_adapter(self, fixtures_path):
        storage_url = f'file://{fixtures_path}'
        client = StorageClient(storage_url=storage_url)
        result = client.component(component_name='example/cmp')

        assert result['download_url'] == os.path.join(
            storage_url, '5390a837-5bc7-4564-b747-3adb22ad55f8.tgz'
        )

    def test_no_registry_token_error(self, monkeypatch, tmp_path):
        monkeypatch.setenv('IDF_COMPONENT_REGISTRY_URL', 'http://localhost:9000')

        client = APIClient(registry_url=get_registry_url())

        file_path = str(tmp_path / 'cmp.tgz')
        with open(file_path, 'w+') as f:
            f.write('a')

        with pytest.raises(APIClientError, match='API token is required'):
            client.upload_version(component_name='example/cmp', file_path=file_path)

    def test_env_var_for_upload_empty(self, monkeypatch):
        monkeypatch.setenv('IDF_COMPONENT_STORAGE_URL', '')
        monkeypatch.setenv('IDF_COMPONENT_REGISTRY_URL', '')
        monkeypatch.setenv('IDF_COMPONENT_API_TOKEN', '')

        registry_url = get_registry_url()
        storage_urls = get_storage_urls()
        assert registry_url == IDF_COMPONENT_REGISTRY_URL
        assert storage_urls == []

    @use_vcr_or_real_env(
        'tests/fixtures/vcr_cassettes/test_no_registry_url_use_static.yaml',
    )
    @pytest.mark.network
    def test_no_registry_url_use_static(self, mock_storage):  # noqa: ARG002
        storage_urls = get_storage_urls()
        client = MultiStorageClient(storage_urls=storage_urls)
        client.component(component_name='test_component_manager/cmp')  # no errors

    @use_vcr_or_real_env('tests/fixtures/vcr_cassettes/test_filter_yanked_version.yaml')
    @pytest.mark.network
    @pytest.mark.parametrize('version', ['=1.0.0', '1.0.0', '==1.0.0,==1.0.0'])
    def test_only_yanked_version_warning(self, storage_url, version, caplog):
        client = StorageClient(storage_url=storage_url)

        with caplog.at_level(logging.WARNING, logger=LOGGING_NAMESPACE):
            client.component(component_name='test_component_manager/stb_and_ynk', version=version)
            assert len(caplog.records) == 1
            assert (
                'The following versions of the "test_component_manager/stb_and_ynk" component have been yanked:'
                in caplog.text
            )

    @use_vcr_or_real_env('tests/fixtures/vcr_cassettes/test_filter_yanked_version.yaml')
    @pytest.mark.network
    @pytest.mark.parametrize(
        'version',
        [
            '>1.0.0',
            '^1.0.0',
            '1.*.*',
            '*',
            None,
        ],
    )
    def test_filter_yanked_version_for_component(self, storage_url, version):
        client = StorageClient(storage_url=storage_url)
        result = client.component(
            component_name='test_component_manager/stb_and_ynk', version=version
        )

        assert result['version'] == '1.0.1'

    @use_vcr_or_real_env('tests/fixtures/vcr_cassettes/test_filter_yanked_version.yaml')
    @pytest.mark.network
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

        result = client.versions(component_name='test_component_manager/stb_and_ynk', spec=spec)
        assert result.versions[0].semver == Version('1.0.1')

    def test_token_information(
        self,
        registry_url,
        mock_registry,  # noqa: ARG002
        mock_token_information,  # noqa: ARG002
    ):
        client = APIClient(registry_url=registry_url, api_token='test')
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

    @use_vcr_or_real_env('tests/fixtures/vcr_cassettes/test_token_information_with_exception.yaml')
    @pytest.mark.network
    def test_token_information_with_exception(self, registry_url):
        client = APIClient(registry_url=registry_url)
        with pytest.raises(Exception):
            client.token_information()

    def test_revoke_token(self, registry_url):
        client = APIClient(registry_url=registry_url, api_token='test')
        with requests_mock.Mocker() as m:
            m.delete(
                'http://localhost:5000/api/tokens/current',
                status_code=204,
            )

            client.revoke_current_token()

            assert m.call_count == 1
            assert m.request_history[0].method == 'DELETE'
            assert m.request_history[0].url == 'http://localhost:5000/api/tokens/current'

    @use_vcr_or_real_env('tests/fixtures/vcr_cassettes/test_version_multiple_storages.yaml')
    @pytest.mark.network
    def test_version_multiple_storages(self, fixtures_path, mock_storage):  # noqa: ARG002
        remote_storage_url = os.environ['IDF_COMPONENT_STORAGE_URL']
        storage_file_path = f'file://{fixtures_path}/'
        storage_urls = [storage_file_path, remote_storage_url]
        client = MultiStorageClient(storage_urls=storage_urls)

        result = client.component(component_name='example/cmp')
        assert result['download_url'].startswith(storage_file_path)

        result = client.component(component_name='test_component_manager/cmp')
        assert result['download_url'].startswith(remote_storage_url)

    def test_upload_component_returns_413_status(self, tmp_path, registry_url, monkeypatch):
        monkeypatch.setattr(
            'idf_component_tools.registry.request_processor.make_request', response_413
        )
        client = APIClient(
            registry_url=registry_url,
            api_token='test',
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

    def test_upload_component_token_forbidden(self, tmp_path, registry_url, monkeypatch):
        messages = ['Your token does not have the required scope: write:components']
        monkeypatch.setattr(
            'idf_component_tools.registry.request_processor.make_request',
            lambda *_, **__: response_403(messages),
        )

        client = APIClient(
            registry_url=registry_url,
            api_token='test',
        )

        (tmp_path / 'cmp.tgz').touch()

        with pytest.raises(APIClientError) as e:
            client.upload_version(
                component_name='kumekay/cmp',
                file_path=tmp_path / 'cmp.tgz',
            )
        assert str(e.value).startswith(messages[0])

    def test_upload_component_role_forbidden(
        self,
        tmp_path,
        registry_url,
        monkeypatch,
    ):
        messages = ['You do not have a required role, to access a']
        monkeypatch.setattr(
            'idf_component_tools.registry.request_processor.make_request',
            lambda *_, **__: response_403(messages),
        )

        client = APIClient(
            registry_url=registry_url,
            api_token='test',
        )

        (tmp_path / 'cmp.tgz').touch()

        with pytest.raises(APIClientError) as e:
            client.upload_version(
                component_name='kumekay/cmp',
                file_path=tmp_path / 'cmp.tgz',
            )
        assert str(e.value).startswith(messages[0])

    def test_upload_component_SSLEOFError(self, tmp_path, registry_url, monkeypatch):
        monkeypatch.setattr(
            'idf_component_tools.registry.request_processor.make_request',
            raise_SSLEOFError,
        )
        client = APIClient(
            registry_url=registry_url,
            api_token='test',
        )

        (tmp_path / 'cmp.tgz').touch()

        with pytest.raises(APIClientError) as e:
            client.upload_version(
                component_name='kumekay/cmp',
                file_path=tmp_path / 'cmp.tgz',
            )
        assert str(e.value).startswith('The component archive exceeds the maximum allowed size')
