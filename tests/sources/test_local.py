import os
import shutil
import tempfile

from idf_component_tools.manifest import ComponentVersion, SolvedComponent
from idf_component_tools.sources import LocalSource


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

    def test_versions_with_manifest(self, cmp_path):
        source = LocalSource(source_details={'path': cmp_path})
        versions = source.versions('cmp', spec='*')

        assert versions.name == 'cmp'
        assert versions.versions[0] == ComponentVersion('1.0.0')

    def test_local_path_name_warning(self, capsys, cmp_path):
        source = LocalSource(source_details={'path': cmp_path})
        component = SolvedComponent('not_cmp', '*', source)
        source.download(component, 'test')

        captured = capsys.readouterr()
        assert 'WARNING:  Component name "espressif/not_cmp" doesn\'t match the directory name "cmp"' in captured.out

    def test_local_path_name_no_warning(self, capsys, cmp_path):
        source = LocalSource(source_details={'path': cmp_path})
        component = SolvedComponent('cmp', '*', source)
        source.download(component, 'test')

        captured = capsys.readouterr()
        assert captured.out == ''
