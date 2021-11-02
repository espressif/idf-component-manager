import filecmp
import os
import shutil
import tempfile

import vcr

from idf_component_tools.hash_tools import hash_dir
from idf_component_tools.manifest import ComponentVersion, SolvedComponent
from idf_component_tools.sources import LocalSource, WebServiceSource

FIXTURE_CMP_PATH = path = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    '..',
    'fixtures',
    'components',
    'cmp',
)


class TestComponentWebServiceSource(object):
    FIXTURE_CMP_HASH = hash_dir(FIXTURE_CMP_PATH)

    EXAMPLE_HASH = 'ed55692af0eed2feb68f6d7a2ef95a0142b20518a53a0ceb7c699795359d7dc5'
    LOCALHOST_HASH = '02d9269ed8690352e6bfc5f6a6c60e859fa6cbfc56efe75a1199b35bdd6c54c8'
    CMP_HASH = '3c29b17da1ce6e0626a520ec8d0fa8763807dd1c13672c4c1939950d0dd865ad'

    def test_service_is_me(self):
        assert WebServiceSource.is_me('test', None)
        assert WebServiceSource.is_me('test', {})
        assert WebServiceSource.is_me('test', {'path': '/'})

    def test_cache_path(self):
        source = WebServiceSource(source_details={'service_url': 'https://example.com/api'})
        component = SolvedComponent('cmp', ComponentVersion('1.0.0'), source=source, component_hash=self.CMP_HASH)
        assert source.component_cache_path(component).endswith(
            'service_{}/espressif__cmp_1.0.0_{}'.format(self.EXAMPLE_HASH[:8], self.CMP_HASH))

    @vcr.use_cassette('tests/fixtures/vcr_cassettes/test_fetch_webservice.yaml')
    def test_download(self):
        tempdir = tempfile.mkdtemp()
        cache_dir = os.path.join(tempdir, 'cache')
        source = WebServiceSource(
            source_details={'service_url': 'https://example.com/api'}, system_cache_path=cache_dir)
        cmp = SolvedComponent('test/cmp', '1.0.1', source, component_hash=self.CMP_HASH)

        try:
            source = WebServiceSource(source_details={'service_url': 'http://localhost:5000/'})
            download_path = os.path.join(tempdir, 'test_download')
            local_path = source.download(cmp, download_path)

            assert len(local_path) == 1
            assert local_path[0] == download_path
            assert os.path.isdir(local_path[0])
            downloaded_manifest = os.path.join(local_path[0], 'idf_component.yml')
            assert os.path.isfile(downloaded_manifest)
            cached_manifest = os.path.join(source.component_cache_path(cmp), 'idf_component.yml')
            assert os.path.isfile(cached_manifest)
            assert filecmp.cmp(downloaded_manifest, cached_manifest)

            # Download one more time, to check that nothing will happen
            source.download(cmp, download_path)

            # Check copy from the cache (NO http request)
            fixture_cmp = SolvedComponent('test/cmp', '1.0.0', source, component_hash=self.FIXTURE_CMP_HASH)
            download_path = os.path.join(tempdir, 'test_cached')
            cache_path = source.component_cache_path(fixture_cmp)
            if os.path.exists(cache_path):
                shutil.rmtree(cache_path, ignore_errors=True)
            shutil.copytree(FIXTURE_CMP_PATH, cache_path)

            local_path = source.download(fixture_cmp, download_path)

            assert os.path.isfile(os.path.join(local_path[0], 'idf_component.yml'))

        finally:
            shutil.rmtree(tempdir)


class TestComponentLocalSource(object):
    def test_service_is_me(self):
        assert LocalSource.is_me('test', {'path': '/'})
        assert not LocalSource.is_me('test', {'url': '/'})

    def test_download(self):
        path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'fixtures')
        source = LocalSource(source_details={'path': path})
        component = SolvedComponent('cmp', '*', source)
        assert source.download(component, '/test/path/')[0].endswith('fixtures')

    def test_versions_without_manifest(self):
        tempdir = tempfile.mkdtemp()

        try:
            source = LocalSource(source_details={'path': tempdir})
            versions = source.versions('test', spec='*')

            assert versions.name == os.path.basename(tempdir)
            assert versions.versions[0] == ComponentVersion('*')

        finally:
            shutil.rmtree(tempdir)

    def test_versions_with_manifest(self):
        source = LocalSource(source_details={'path': FIXTURE_CMP_PATH})
        versions = source.versions('cmp', spec='*')

        assert versions.name == 'cmp'
        assert versions.versions[0] == ComponentVersion('1.0.0')
