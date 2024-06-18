# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import filecmp
import os
import shutil

import pytest
import vcr

from idf_component_tools.errors import FetchingError
from idf_component_tools.hash_tools.calculate import hash_dir
from idf_component_tools.manager import ManifestManager
from idf_component_tools.manifest import SolvedComponent
from idf_component_tools.messages import UserHint
from idf_component_tools.sources import WebServiceSource
from idf_component_tools.sources.web_service import download_archive
from idf_component_tools.utils import ComponentVersion


class TestComponentWebServiceSource:
    EXAMPLE_HASH = '73d986e009065f182c10bcb6a45db3d6eda9498f8930654af2653f8a938cd801'
    LOCALHOST_HASH = '02d9269ed8690352e6bfc5f6a6c60e859fa6cbfc56efe75a1199b35bdd6c54c8'
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
    @vcr.use_cassette('tests/fixtures/vcr_cassettes/test_fetch_webservice.yaml')
    def test_download(self, monkeypatch, release_component_path, tmp_path):
        monkeypatch.setenv('IDF_COMPONENT_REGISTRY_URL', 'http://localhost:5000')

        cache_dir = str(tmp_path / 'cache')
        monkeypatch.setenv('IDF_COMPONENT_CACHE_PATH', cache_dir)

        source = WebServiceSource(
            registry_url='https://example.com/api', system_cache_path=cache_dir
        )
        # without 'api'
        assert source.registry_url == 'https://example.com'

        cmp = SolvedComponent(
            name='test/cmp',
            version=ComponentVersion('1.0.1'),
            source=source,
            component_hash=self.CMP_HASH,
        )

        download_path = str(tmp_path / 'test_download')
        local_path = source.download(cmp, download_path)

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
            name='test/cmp',
            version=ComponentVersion('1.0.0'),
            source=source,
            component_hash=hash_dir(
                release_component_path,
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

    @vcr.use_cassette('tests/fixtures/vcr_cassettes/test_webservice_pre_release.yaml')
    def test_pre_release_exists(self, capsys):
        source = WebServiceSource(registry_url='http://localhost:5000/')

        with pytest.warns(UserHint) as record:
            versions = source.versions('example/cmp')

            prerelease_hint_str = (
                'Component "example/cmp" has some pre-release versions: "0.0.5-alpha1" '
                'satisfies your requirements. '
                'To allow pre-release versions add "pre_release: true" '
                'to the dependency in the manifest.'
            )

            assert prerelease_hint_str in record.list[0].message.args
            assert versions.versions == []

    @vcr.use_cassette('tests/fixtures/vcr_cassettes/test_webservice_pre_release.yaml')
    def test_pre_release_exists_with_pre_release_spec(self, monkeypatch):
        source = WebServiceSource(registry_url='http://localhost:5000/')

        source.versions('example/cmp', spec='^0.0.5-alpha1')

    @vcr.use_cassette('tests/fixtures/vcr_cassettes/test_webservice_versions.yaml')
    def test_skip_pre_release(self):
        source = WebServiceSource(registry_url='http://localhost:5000/', pre_release=False)
        assert len(source.versions('example/cmp').versions) == 1

    @vcr.use_cassette('tests/fixtures/vcr_cassettes/test_webservice_versions.yaml')
    def test_select_pre_release(self):
        source = WebServiceSource(registry_url='http://localhost:5000/', pre_release=True)
        assert len(source.versions('example/cmp').versions) == 2

    @vcr.use_cassette('tests/fixtures/vcr_cassettes/test_webservice_target.yaml')
    def test_target_exists(self, monkeypatch):
        source = WebServiceSource(registry_url='http://localhost:5000/')

        with pytest.warns(UserHint) as record:
            versions = source.versions('example/cmp', target='esp32s2')

            other_targets_hint_str = (
                'Component "example/cmp" has suitable versions for other targets: "esp32". '
                'Is your current target "esp32s2" set correctly?'
            )

            assert other_targets_hint_str in record[0].message.args
            assert versions.versions == []
