import os
import shutil
import tempfile

from component_manager.manifest import ManifestParser


class TestManifestParser(object):
    def test_check_filename(self, capsys):
        parser = ManifestParser("some/path/manifest.yaml")

        parser.check_filename()

        captured = capsys.readouterr()
        assert captured.out.startswith("Warning")

    def test_init_manifest(self):
        tempdir = tempfile.mkdtemp()
        manifest_path = os.path.join(tempdir, "manifest.yml")
        parser = ManifestParser(manifest_path)

        parser.init_manifest()

        with open(manifest_path, "r") as f:
            assert f.readline().startswith("## Espressif")

        shutil.rmtree(tempdir)
