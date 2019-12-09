import os
import shutil
import tempfile

import vcr

from idf_component_manager.component_sources.local import LocalSource
from idf_component_manager.component_sources.web_service import WebServiceSource
from idf_component_manager.manifest import ComponentVersion
from idf_component_manager.version_solver.solver_result import SolvedComponent


class TestComponentWebServiceSource(object):
    EXAMPLE_HASH = 'ed55692af0eed2feb68f6d7a2ef95a0142b20518a53a0ceb7c699795359d7dc5'
    LOCALHOST_HASH = '1fca862736e33907fa706af6ba0eb960b553aef36cdf60690edb7b0c49a8e96b'

    def test_service_is_me(self):
        assert WebServiceSource.is_me('test', None)
        assert WebServiceSource.is_me('test', {})
        assert WebServiceSource.is_me('test', {'path': '/'})

    def test_unique_path(self):
        source = WebServiceSource(source_details={'service_url': 'https://example.com/api'})
        assert (source.unique_path('cmp', '1.0.0') == 'cmp~1.0.0~%s' % self.EXAMPLE_HASH)

    @vcr.use_cassette('fixtures/vcr_cassettes/test_fetch_webservice.yaml')
    def test_download(self):
        tempdir = tempfile.mkdtemp()
        source = WebServiceSource(source_details={'service_url': 'https://example.com/api'})
        cmp = SolvedComponent('cmp', '0.0.1', source, component_hash=self.EXAMPLE_HASH)

        try:
            source = WebServiceSource(source_details={'service_url': 'http://127.0.0.1:8000/api'})
            download_path = os.path.join(tempdir, 'cmp~0.0.1~%s' % self.LOCALHOST_HASH)
            local_path = source.download(cmp, download_path)

            assert local_path == download_path
            assert os.path.isdir(local_path)
            assert os.path.isfile(os.path.join(local_path, 'idf_component.yml'))

        finally:
            shutil.rmtree(tempdir)


class TestComponentLocalSource(object):
    def test_service_is_me(self):
        assert LocalSource.is_me('test', {'path': '/'})
        assert not LocalSource.is_me('test', {'url': '/'})

    def test_download(self):
        path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'manifests')
        source = LocalSource(source_details={'path': path})
        component = SolvedComponent('cmp', '*', source)
        assert source.download(component, '/test/path/').endswith('manifests')

    def test_versions_without_manifest(self):

        tempdir = tempfile.mkdtemp()

        try:
            source = LocalSource(source_details={'path': tempdir})
            versions = source.versions('test', spec='*')

            assert versions.name == 'test'
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
        versions = source.versions('test', spec='*')

        assert versions.name == 'test'
        assert versions.versions[0] == ComponentVersion('1.0.0')
