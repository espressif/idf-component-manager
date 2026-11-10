# SPDX-FileCopyrightText: 2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
"""Tests for sending the API token on registry read/download requests."""

import requests_mock

from idf_component_tools.registry.multi_storage_client import MultiStorageClient
from idf_component_tools.registry.storage_client import StorageClient
from idf_component_tools.sources.web_service import download_file


class TestStorageClientToken:
    def test_metadata_request_sends_token(self):
        client = StorageClient(storage_url='http://storage.example/a', token='secret')
        with requests_mock.Mocker() as m:
            m.get(requests_mock.ANY, json={})
            client.get_component_json(component_name='espressif/cmp')

            assert m.request_history[-1].headers['Authorization'] == 'Bearer secret'

    def test_metadata_request_without_token_is_anonymous(self):
        client = StorageClient(storage_url='http://storage.example/b')
        with requests_mock.Mocker() as m:
            m.get(requests_mock.ANY, json={})
            client.get_component_json(component_name='espressif/cmp')

            assert 'Authorization' not in m.request_history[-1].headers


class TestMultiStorageClientTokenScope:
    def _client(self, api_token=None):
        client = MultiStorageClient(
            registry_url='http://registry.example', api_token=api_token
        )
        with requests_mock.Mocker() as m:
            m.get(
                'http://registry.example/api',
                json={
                    'components_base_url': 'http://storage.example/registry',
                    'info': 'test',
                    'status': 'ok',
                    'version': '1.0.0',
                },
            )
            # Resolve (and cache) the registry storage url while mocked.
            assert client.registry_storage_url == 'http://storage.example/registry'
        return client

    def test_token_used_for_registry_storage(self):
        client = self._client(api_token='secret')

        assert (
            client.token_for_url('http://storage.example/registry/components/a/b.zip')
            == 'secret'
        )

    def test_token_not_leaked_to_other_hosts(self):
        client = self._client(api_token='secret')

        assert client.token_for_url('http://other.example/components/a/b.zip') is None

    def test_no_token_configured(self):
        client = self._client(api_token=None)

        assert (
            client.token_for_url('http://storage.example/registry/components/a/b.zip')
            is None
        )


class TestDownloadFileToken:
    def test_download_sends_token(self, tmp_path):
        url = 'http://storage.example/registry/components/a/b/file.tgz'
        with requests_mock.Mocker() as m:
            m.get(url, content=b'data')
            download_file(url, str(tmp_path), filename='file.tgz', token='secret')

            assert m.request_history[-1].headers['Authorization'] == 'Bearer secret'

    def test_download_without_token_is_anonymous(self, tmp_path):
        url = 'http://storage.example/registry/components/a/b/file2.tgz'
        with requests_mock.Mocker() as m:
            m.get(url, content=b'data')
            download_file(url, str(tmp_path), filename='file2.tgz')

            assert 'Authorization' not in m.request_history[-1].headers