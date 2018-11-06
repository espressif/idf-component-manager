import os
import shutil
import tempfile
from collections import OrderedDict
from copy import deepcopy

import pytest

from component_manager.manifest import ManifestPipeline, ManifestValidator


class TestManifestPipeline(object):
    def test_check_filename(self, capsys):
        parser = ManifestPipeline("some/path/manifest.yaml")

        parser.check_filename()

        captured = capsys.readouterr()
        assert captured.out.startswith("Warning")

    def test_init_manifest(self):
        tempdir = tempfile.mkdtemp()
        manifest_path = os.path.join(tempdir, "manifest.yml")
        parser = ManifestPipeline(manifest_path)

        parser.init_manifest()

        with open(manifest_path, "r") as f:
            assert f.readline().startswith("## Espressif")

        shutil.rmtree(tempdir)

    def test_parse_invalid_yaml(self, capsys):
        manifest_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "manifests", "invalid_yaml.yml"
        )
        parser = ManifestPipeline(manifest_path)

        with pytest.raises(SystemExit) as e:
            parser.manifest_tree

        captured = capsys.readouterr()
        assert e.type == SystemExit
        assert e.value.code == 1
        assert captured.out.startswith("Error")

    def test_parse_valid_yaml(self, capsys):
        manifest_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "manifests", "manifest.yml"
        )
        parser = ManifestPipeline(manifest_path)

        assert len(parser.manifest_tree.keys()) == 5

    def test_build(self):
        manifest_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "manifests", "manifest.yml"
        )
        parser = ManifestPipeline(manifest_path).prepare()

        parser.build()
        manifest = parser.manifest

        assert len(manifest.components) == 3

    def test_prepare(self):
        manifest_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "manifests", "manifest.yml"
        )
        parser = ManifestPipeline(manifest_path)

        parser.prepare()

        assert parser.is_valid


class TestManifestValidator(object):
    VALID_MANIFEST = OrderedDict(
        {
            "idf_version": "~4.4.4",
            "version": "2.3.1",
            "platforms": ["esp32"],
            "maintainer": "Test Tester <test@example.com>",
            "components": {
                "test": {"version": ">=8.2.0,<9.0.0"},
                "test-1": "^1.2.7",
                "test-8": {"version": ""},
                "test-2": "",
                "test-4": "*",
                "some_component": {"version": "!=1.2.7"},
            },
        }
    )

    def test_validate_unknown_root_key(self):
        manifest = deepcopy(self.VALID_MANIFEST)
        manifest["unknown"] = "test"
        manifest["test"] = "test"
        validator = ManifestValidator(manifest)

        errors = validator.validate_normalize()

        assert len(errors) == 1
        assert errors[0].startswith("Unknown keys: unknown, test")

    def test_validate_unknown_root_values(self):
        manifest = deepcopy(self.VALID_MANIFEST)
        manifest["version"] = "1!.3.3"
        manifest["idf_version"] = ">12...32"
        validator = ManifestValidator(manifest)

        errors = validator.validate_normalize()

        assert len(errors) == 2
        assert errors[0].startswith("Project version should be valid")
        assert errors[1].startswith('Version specifications for "idf_version"')

    def test_validate_component_versions_not_in_manifest(self):
        manifest = deepcopy(self.VALID_MANIFEST)
        manifest.pop("components")
        validator = ManifestValidator(manifest)

        errors = validator.validate_normalize()

        assert not errors

    def test_validate_component_version_normalization(self):
        manifest = deepcopy(self.VALID_MANIFEST)
        manifest["components"] = {"test": "1.2.3", "pest": {"version": "3.2.1"}}
        validator = ManifestValidator(manifest)

        errors = validator.validate_normalize()

        assert not errors
        assert validator.manifest_tree["components"] == {
            "test": {"version": "1.2.3"},
            "pest": {"version": "3.2.1"},
        }

    def test_validate_component_versions_are_empty(self):
        manifest = deepcopy(self.VALID_MANIFEST)
        manifest["components"] = {}
        validator = ManifestValidator(manifest)

        errors = validator.validate_normalize()

        assert not errors

    def test_validate_component_versions_not_a_dict(self):
        manifest = deepcopy(self.VALID_MANIFEST)
        manifest["components"] = ["one_component", "another-one"]
        validator = ManifestValidator(manifest)

        errors = validator.validate_normalize()

        assert len(errors) == 1
        assert errors[0].startswith("List of components should be a dictionary")

    def test_validate_component_versions_unknown_key(self):
        manifest = deepcopy(self.VALID_MANIFEST)
        manifest["components"] = {
            "test-component": {"version": "^1.2.3", "persion": "asdf"}
        }
        validator = ManifestValidator(manifest)

        errors = validator.validate_normalize()

        assert len(errors) == 1
        assert errors[0] == 'Unknown attributes for component "test-component": persion'

    def test_validate_component_versions_invalid_name(self):
        manifest = deepcopy(self.VALID_MANIFEST)
        manifest["components"] = {"asdf!fdsa": {"version": "^1.2.3"}}
        validator = ManifestValidator(manifest)

        errors = validator.validate_normalize()

        assert len(errors) == 1
        assert errors[0].startswith('Component\'s name is not valid "asdf!fdsa",')

    def test_validate_component_versions_invalid_spec_subkey(self):
        manifest = deepcopy(self.VALID_MANIFEST)
        manifest["components"] = {"test-component": {"version": "^1.2a.3"}}
        validator = ManifestValidator(manifest)

        errors = validator.validate_normalize()

        assert len(errors) == 1
        assert errors[0].startswith(
            'Version specifications for "test-component" are invalid.'
        )

    def test_validate_component_versions_invalid_spec(self):
        manifest = deepcopy(self.VALID_MANIFEST)
        manifest["components"] = {"test-component": "~=1a.2.3"}
        validator = ManifestValidator(manifest)

        errors = validator.validate_normalize()

        assert len(errors) == 1
        assert errors[0].startswith(
            'Version specifications for "test-component" are invalid.'
        )

    def test_validate_platforms_unknown(self):
        manifest = deepcopy(self.VALID_MANIFEST)
        manifest["platforms"] = ["esp123", "esp32", "asdf"]
        validator = ManifestValidator(manifest)

        errors = validator.validate_normalize()

        assert len(errors) == 1
        assert errors[0].startswith("Unknown platforms: esp123, asdf")

    def test_slug_re(self):
        valid_names = ("asdf-fadsf", "_", "-", "_good", "123", "asdf-_-fdsa-")
        invalid_names = ("!", "asdf$f", "daf411~", "adf\nadsf")

        slug_re = ManifestValidator.SLUG_RE

        for name in valid_names:
            assert slug_re.match(name)

        for name in invalid_names:
            assert not slug_re.match(name)

    def test_validate_version_list(self):
        validator = ManifestValidator(self.VALID_MANIFEST)

        errors = validator.validate_normalize()

        assert not errors
