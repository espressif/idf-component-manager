import os

import pytest

from idf_component_tools.errors import ManifestError
from idf_component_tools.manifest import ManifestManager, ManifestValidator
from idf_component_tools.manifest.validator import SLUG_RE


class TestManifestPipeline(object):
    def test_check_filename(self, capsys):
        parser = ManifestManager('some/path/idf_component.yaml')

        parser.check_filename()

        captured = capsys.readouterr()
        assert captured.out.startswith('Warning')

    def test_parse_invalid_yaml(self):
        manifest_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'fixtures', 'invalid_yaml.yml')
        parser = ManifestManager(manifest_path)

        with pytest.raises(ManifestError) as e:
            parser.manifest_tree

        assert e.type == ManifestError
        assert str(e.value).startswith('Cannot parse manifest file')

    def test_parse_valid_yaml(self, capsys):
        manifest_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'fixtures', 'idf_component.yml')
        parser = ManifestManager(manifest_path)

        assert len(parser.manifest_tree.keys()) == 7

    def test_prepare(self):
        manifest_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'fixtures', 'idf_component.yml')
        parser = ManifestManager(manifest_path)

        parser.load()

        assert parser.is_valid


class TestManifestValidator(object):
    def test_validate_unknown_root_key(self, valid_manifest):
        valid_manifest['unknown'] = 'test'
        valid_manifest['test'] = 'test'
        validator = ManifestValidator(valid_manifest)

        errors = validator.validate_normalize()

        assert len(errors) == 1
        assert errors[0].startswith('Unknown keys: test, unknown')

    def test_validate_unknown_root_values(self, valid_manifest):
        valid_manifest['version'] = '1!.3.3'
        validator = ManifestValidator(valid_manifest)

        errors = validator.validate_normalize()

        assert len(errors) == 1
        assert errors[0].startswith('Component version should be valid')

    def test_validate_component_versions_not_in_manifest(self, valid_manifest):
        valid_manifest.pop('dependencies')
        validator = ManifestValidator(valid_manifest)

        errors = validator.validate_normalize()

        assert not errors

    def test_validate_component_version_normalization(self, valid_manifest):
        valid_manifest['dependencies'] = {'test': '1.2.3', 'pest': {'version': '3.2.1'}}
        validator = ManifestValidator(valid_manifest)

        errors = validator.validate_normalize()

        assert not errors
        assert validator.manifest_tree['dependencies'] == {
            'test': {
                'version': '1.2.3'
            },
            'pest': {
                'version': '3.2.1'
            },
        }

    def test_validate_component_versions_are_empty(self, valid_manifest):
        valid_manifest['dependencies'] = {}
        validator = ManifestValidator(valid_manifest)

        errors = validator.validate_normalize()

        assert not errors

    def test_validate_component_versions_not_a_dict(self, valid_manifest):
        valid_manifest['dependencies'] = ['one_component', 'another-one']
        validator = ManifestValidator(valid_manifest)

        errors = validator.validate_normalize()

        assert len(errors) == 1
        assert errors[0].startswith('List of dependencies should be a dictionary')

    def test_validate_component_versions_unknown_key(self, valid_manifest):
        valid_manifest['dependencies'] = {'test-component': {'version': '^1.2.3', 'persion': 'asdf'}}
        validator = ManifestValidator(valid_manifest)

        errors = validator.validate_normalize()

        assert len(errors) == 1
        assert errors[0] == 'Unknown attributes for component "test-component": persion'

    def test_validate_component_versions_invalid_name(self, valid_manifest):
        valid_manifest['dependencies'] = {'asdf!fdsa': {'version': '^1.2.3'}}
        validator = ManifestValidator(valid_manifest)

        errors = validator.validate_normalize()

        assert len(errors) == 1
        assert errors[0].startswith('Component\'s name is not valid "asdf!fdsa",')

    def test_validate_component_versions_invalid_spec_subkey(self, valid_manifest):
        valid_manifest['dependencies'] = {'test-component': {'version': '^1.2a.3'}}
        validator = ManifestValidator(valid_manifest)

        errors = validator.validate_normalize()

        assert len(errors) == 1
        assert errors[0].startswith('Version specifications for "test-component" are invalid.')

    def test_validate_component_versions_invalid_spec(self, valid_manifest):
        valid_manifest['dependencies'] = {'test-component': '~=1a.2.3'}
        validator = ManifestValidator(valid_manifest)

        errors = validator.validate_normalize()

        assert len(errors) == 1
        assert errors[0].startswith('Version specifications for "test-component" are invalid.')

    def test_validate_targets_unknown(self, valid_manifest):
        valid_manifest['targets'] = ['esp123', 'esp32', 'asdf']
        validator = ManifestValidator(valid_manifest)

        errors = validator.validate_normalize()

        assert len(errors) == 1
        assert errors[0].startswith('Unknown targets: esp123, asdf')

    def test_slug_re(self):
        valid_names = ('asdf-fadsf', '_', '-', '_good', '123', 'asdf-_-fdsa-')
        invalid_names = ('!', 'asdf$f', 'daf411~', 'adf\nadsf')

        for name in valid_names:
            assert SLUG_RE.match(name)

        for name in invalid_names:
            assert not SLUG_RE.match(name)

    def test_validate_version_list(self, valid_manifest):
        validator = ManifestValidator(valid_manifest)

        errors = validator.validate_normalize()

        assert not errors

    def test_check_required_keys(self, valid_manifest):
        validator = ManifestValidator(valid_manifest, check_required_fields=True)

        errors = validator.validate_normalize()

        assert not errors

    def test_check_required_keys_empty_manifest(self):
        validator = ManifestValidator({}, check_required_fields=True)

        errors = validator.validate_normalize()

        assert len(errors) == 2
