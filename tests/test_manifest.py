import os
import shutil
import tempfile
from copy import deepcopy

import pytest

from component_manager.manifest import ManifestParser, ManifestValidator


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

    def test_parse_invalid_yaml(self, capsys):
        manifest_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "manifests", "invalid_yaml.yml"
        )
        parser = ManifestParser(manifest_path)

        with pytest.raises(SystemExit) as e:
            parser.manifest

        captured = capsys.readouterr()
        assert e.type == SystemExit
        assert e.value.code == 1
        assert captured.out.startswith("Error")

    def test_parse_valid_yaml(self, capsys):
        manifest_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "manifests", "manifest.yml"
        )
        parser = ManifestParser(manifest_path)

        assert len(parser.manifest.keys()) == 5


class TestManifestValidator(object):
    VALID_MANIFEST = {
        "idf-version": "~4.4.4",
        "version": "2.3.1",
        "platforms": ["esp32"],
        "maintainer": "Test Tester <test@example.com>",
        "components": {
            "test": {"version": ">=8.2.0 <9.0.0"},
            "test-1": "^1.2.7",
            "some_component": {"version": "~1.2.7"},
        },
    }

    def test_validate_unknown_root_directive(self):
        manifest = deepcopy(self.VALID_MANIFEST)
        manifest["unknown"] = "test"
        manifest["test"] = "test"
        validator = ManifestValidator(manifest)

        errors = validator.validate()

        assert len(errors) == 2
        assert errors[0] == "Unknown root directive: unknown"

    def test_validate_version_list(self):
        validator = ManifestValidator(self.VALID_MANIFEST)

        errors = validator.validate()

        assert not errors
