# SPDX-FileCopyrightText: 2022-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import filecmp
import os
import shutil

import pytest

from idf_component_tools.errors import FetchingError
from idf_component_tools.hash_tools.calculate import hash_dir
from idf_component_tools.manager import ManifestManager
from idf_component_tools.manifest import SolvedComponent
from idf_component_tools.sources import WebServiceSource
from idf_component_tools.sources.web_service import download_archive
from idf_component_tools.utils import ComponentVersion
from tests.network_test_utils import use_vcr_or_real_env


class TestComponentWebServiceSource:
    # pragma: allowlist nextline secret
    EXAMPLE_HASH = '73d986e009065f182c10bcb6a45db3d6eda9498f8930654af2653f8a938cd801'
    # pragma: allowlist nextline secret
    LOCALHOST_HASH = '02d9269ed8690352e6bfc5f6a6c60e859fa6cbfc56efe75a1199b35bdd6c54c8'
    # pragma: allowlist nextline secret
    CMP_HASH = '15a658f759a13f1767ca3810cd822e010aba1e36b3a980d140cc5e80e823f422'

    def test_cache_path(self):
        source = WebServiceSource(registry_url='https://example.com/api')
        component = SolvedComponent(
            name='cmp',
            version=ComponentVersion('1.0.0'),
            source=source,
            component_hash=self.CMP_HASH,
        )
        assert source.component_cache_path(component).endswith(
            f'service_{self.EXAMPLE_HASH[:8]}/espressif__cmp_1.0.0_{self.CMP_HASH[:8]}'
        )

    # If you re-record this cassette, make sure the file downloaded only once
    @use_vcr_or_real_env('tests/fixtures/vcr_cassettes/test_fetch_webservice.yaml')
    @pytest.mark.network
    def test_download(self, monkeypatch, release_component_path, tmp_path):
        monkeypatch.setenv('IDF_COMPONENT_REGISTRY_URL', 'http://example.com')

        cache_dir = str(tmp_path / 'cache')
        monkeypatch.setenv('IDF_COMPONENT_CACHE_PATH', cache_dir)

        source = WebServiceSource(
            registry_url='http://localhost:5000',  # use a different registry_url for testing
            system_cache_path=cache_dir,
        )
        cmp = SolvedComponent(
            name='test_component_manager/cmp',
            version=ComponentVersion('1.0.1'),
            source=source,
            component_hash=self.CMP_HASH,
        )

        download_path = str(tmp_path / 'test_download')
        local_path = source.download(cmp, download_path)  # first download shall download something

        assert local_path == download_path
        assert os.path.isdir(local_path)
        downloaded_manifest = os.path.join(local_path, 'idf_component.yml')
        assert os.path.isfile(downloaded_manifest)
        cached_manifest = os.path.join(source.component_cache_path(cmp), 'idf_component.yml')
        assert os.path.isfile(cached_manifest)
        assert filecmp.cmp(downloaded_manifest, cached_manifest)

        # Download one more time, to check that nothing will happen
        source.download(cmp, download_path)

        # Check copy from the cache (NO http request)

        # release_component_path shouldn't have any excluded files.
        # It's "downloaded" from the registry
        manifest_manager = ManifestManager(release_component_path, 'cmp')
        manifest = manifest_manager.load()

        fixture_cmp = SolvedComponent(
            name='test_component_manager/cmp',
            version=ComponentVersion('1.0.0'),
            source=source,
            component_hash=hash_dir(
                release_component_path,
                use_gitignore=manifest.use_gitignore,
                include=manifest.include_set,
                exclude=manifest.exclude_set,
                exclude_default=False,
            ),
        )
        download_path = str(tmp_path / 'test_cached')
        cache_path = source.component_cache_path(fixture_cmp)
        if os.path.exists(cache_path):
            shutil.rmtree(cache_path, ignore_errors=True)
        shutil.copytree(release_component_path, cache_path)

        local_path = source.download(fixture_cmp, download_path)

        assert os.path.isfile(os.path.join(local_path, 'idf_component.yml'))

    def test_download_local_file(self, fixtures_path, tmp_path):
        source_file = os.path.join(fixtures_path, 'archives', 'cmp_1.0.0.tar.gz')

        file = download_archive(f'file://{source_file}', str(tmp_path))
        assert filecmp.cmp(source_file, file)

    def test_download_local_file_not_existing(self, tmp_path):
        source_file = os.path.join(str(tmp_path), 'cmp_1.0.0.tar.gz')

        with pytest.raises(FetchingError):
            download_archive(f'file://{source_file}', tmp_path)

    @use_vcr_or_real_env('tests/fixtures/vcr_cassettes/test_webservice_pre_release.yaml')
    @pytest.mark.network
    def test_pre_release_exists_with_pre_release_spec(self, mock_registry):
        registry_url = os.getenv('IDF_COMPONENT_REGISTRY_URL', 'http://localhost:5000')
        source = WebServiceSource(registry_url=registry_url)

        source.versions('test_component_manager/pre', spec='^0.0.5-alpha1')

    @use_vcr_or_real_env('tests/fixtures/vcr_cassettes/test_webservice_versions.yaml')
    @pytest.mark.network
    def test_skip_pre_release(self, mock_registry):
        registry_url = os.getenv('IDF_COMPONENT_REGISTRY_URL', 'http://localhost:5000')
        source = WebServiceSource(registry_url=registry_url, pre_release=False)
        assert len(source.versions('test_component_manager/cmp').versions) == 2

    @use_vcr_or_real_env('tests/fixtures/vcr_cassettes/test_webservice_versions.yaml')
    @pytest.mark.network
    def test_select_pre_release(self, mock_registry):
        registry_url = os.getenv('IDF_COMPONENT_REGISTRY_URL', 'http://localhost:5000')
        source = WebServiceSource(registry_url=registry_url, pre_release=True)
        assert len(source.versions('test_component_manager/cmp').versions) == 3


def test_webservice_normalized_name():
    assert WebServiceSource().normalized_name('cmp') == 'espressif/cmp'
