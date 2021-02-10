import os
import shutil
import tempfile

import vcr

from idf_component_tools.manifest import ComponentVersion, SolvedComponent
from idf_component_tools.sources import LocalSource, WebServiceSource


class TestComponentWebServiceSource(object):
    EXAMPLE_HASH = 'ed55692af0eed2feb68f6d7a2ef95a0142b20518a53a0ceb7c699795359d7dc5'
    LOCALHOST_HASH = '02d9269ed8690352e6bfc5f6a6c60e859fa6cbfc56efe75a1199b35bdd6c54c8'

    def test_service_is_me(self):
        assert WebServiceSource.is_me('test', None)
        assert WebServiceSource.is_me('test', {})
        assert WebServiceSource.is_me('test', {'path': '/'})

    def test_unique_path(self):
        source = WebServiceSource(source_details={'service_url': 'https://example.com/api'})
        assert source.unique_path('cmp', '1.0.0') == ('cmp~1.0.0~%s' % self.EXAMPLE_HASH)

    @vcr.use_cassette('tests/fixtures/vcr_cassettes/test_fetch_webservice.yaml')
    def test_download(self):
        tempdir = tempfile.mkdtemp()
        source = WebServiceSource(source_details={'service_url': 'https://example.com/api'})
        cmp = SolvedComponent('test/cmp', '1.0.1', source, component_hash=self.EXAMPLE_HASH)

        try:
            source = WebServiceSource(source_details={'service_url': 'http://localhost:5000/'})
            download_path = os.path.join(tempdir, 'cmp~0.0.1~%s' % self.LOCALHOST_HASH)
            local_path = source.download(cmp, download_path)

            assert len(local_path) == 1
            assert local_path[0] == download_path
            assert os.path.isdir(local_path[0])
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
        path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            '..',
            'fixtures',
            'components',
            'cmp',
        )
        source = LocalSource(source_details={'path': path})
        versions = source.versions('cmp', spec='*')

        assert versions.name == 'cmp'
        assert versions.versions[0] == ComponentVersion('1.0.0')
