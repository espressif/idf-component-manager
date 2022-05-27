import os
import re

import pytest
import yaml

from idf_component_manager.dependencies import detect_unused_components
from idf_component_tools.errors import ManifestError
from idf_component_tools.manifest import (
    SLUG_REGEX, ComponentVersion, ManifestManager, ManifestValidator, SolvedComponent)
from idf_component_tools.manifest.validator import DEFAULT_KNOWN_TARGETS, known_targets, parse_if_clause
from idf_component_tools.sources import LocalSource


class TestComponentVersion(object):
    def test_comparison(self):
        versions = [
            ComponentVersion('3.0.4'),
            ComponentVersion('3.0.6'),
            ComponentVersion('3.0.5'),
        ]

        assert versions[0] == ComponentVersion('3.0.4')
        assert versions[0] != ComponentVersion('*')
        assert versions[0] != ComponentVersion('699d3202533d13b55df3021d93352d8c242ee81e')
        assert str(max(versions)) == '3.0.6'

    def test_flags(self):
        semver = ComponentVersion('1.2.3')
        assert semver.is_semver
        assert not semver.is_commit_id
        assert not semver.is_any

        semver = ComponentVersion('*')
        assert not semver.is_semver
        assert not semver.is_commit_id
        assert semver.is_any

        semver = ComponentVersion('699d3202533d13b55df3021d93352d8c242ee81e')
        assert not semver.is_semver
        assert semver.is_commit_id
        assert not semver.is_any


class TestManifestPipeline(object):
    def test_check_filename(self, tmp_path):
        path = tmp_path.as_posix()
        parser = ManifestManager(path, name='test')

        parser.check_filename()

        assert parser._path == os.path.join(path, 'idf_component.yml')

    def test_parse_invalid_yaml(self):
        manifest_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'fixtures', 'invalid_yaml.yml')
        parser = ManifestManager(manifest_path, name='fixtures')

        with pytest.raises(ManifestError) as e:
            parser.manifest_tree

        assert e.type == ManifestError
        assert str(e.value).startswith('Cannot parse')

    def test_parse_valid_yaml(self, capsys):
        manifest_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'fixtures', 'idf_component.yml')
        parser = ManifestManager(manifest_path, name='fixtures')

        assert len(parser.manifest_tree.keys()) == 7

    def test_prepare(self):
        manifest_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'fixtures', 'idf_component.yml')
        parser = ManifestManager(manifest_path, name='fixtures')

        parser.load()

        assert parser.is_valid

    def test_env_var(self, valid_manifest, monkeypatch, tmp_path):
        monkeypatch.setenv('SUPPORT_TARGET', 'esp32s2')
        valid_manifest['targets'] = ['$SUPPORT_TARGET']

        manifest_path = os.path.join(str(tmp_path), 'idf_component.yml')
        with open(manifest_path, 'w') as fw:
            yaml.dump(valid_manifest, fw)

        parser = ManifestManager(manifest_path, name='test')
        parser.load()

        assert parser.manifest_tree['targets'] == ['esp32s2']

    def test_env_var_not_specified(self, valid_manifest, monkeypatch, tmp_path):
        valid_manifest['targets'] = ['$SUPPORT_TARGET']

        manifest_path = os.path.join(str(tmp_path), 'idf_component.yml')
        with open(manifest_path, 'w') as fw:
            yaml.dump(valid_manifest, fw)

        parser = ManifestManager(manifest_path, name='test')
        with pytest.raises(
                ManifestError,
                match='Using environment variable "SUPPORT_TARGET" in the manifest file but not specifying it'):
            parser.load()


class TestManifestValidator(object):
    def test_validate_unknown_root_key(self, valid_manifest):
        valid_manifest['unknown'] = 'test'
        valid_manifest['test'] = 'test'
        validator = ManifestValidator(valid_manifest)

        errors = validator.validate_normalize()

        assert len(errors) == 2
        assert errors[1].startswith('Unknown keys: test, unknown')

    def test_validate_unknown_root_values(self, valid_manifest):
        valid_manifest['version'] = '1!.3.3'
        validator = ManifestValidator(valid_manifest)

        errors = validator.validate_normalize()

        assert len(errors) == 2
        assert errors[1].startswith('Component version should be valid')

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

        assert len(errors) == 2
        assert errors[1].startswith('List of dependencies should be a dictionary')

    def test_validate_component_versions_unknown_key(self, valid_manifest):
        valid_manifest['dependencies'] = {'test-component': {'version': '^1.2.3', 'persion': 'asdf'}}
        validator = ManifestValidator(valid_manifest)

        errors = validator.validate_normalize()

        assert len(errors) == 4
        assert errors[3] == 'Unknown keys in dependency details: persion'

    def test_validate_component_versions_invalid_name(self, valid_manifest):
        valid_manifest['dependencies'] = {'asdf!fdsa': {'version': '^1.2.3'}}
        validator = ManifestValidator(valid_manifest)

        errors = validator.validate_normalize()

        assert len(errors) == 2
        assert errors[1].startswith('Component\'s name is not valid "asdf!fdsa",')

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

        assert len(errors) == 2
        assert errors[1].startswith('Unknown targets: esp123, asdf')

    def test_slug_re(self):
        valid_names = ('asdf-fadsf', '123', 'asdf_erw', 'as_df_erw', 'test-stse-sdf_sfd')
        invalid_names = ('!', 'asdf$f', 'daf411~', 'adf\nadsf', '_', '-', '_good', 'asdf-_-fdsa-')

        for name in valid_names:
            assert re.match(SLUG_REGEX, name)

        for name in invalid_names:
            assert not re.match(SLUG_REGEX, name)

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

        assert len(errors) == 1

    def test_validate_files_invalid_format(self, valid_manifest):
        valid_manifest['files']['include'] = 34
        validator = ManifestValidator(valid_manifest)
        errors = validator.validate_normalize()

        assert len(errors) == 1

    def test_validate_files_invalid_path(self, valid_manifest):
        valid_manifest['files']['include'] = 34
        validator = ManifestValidator(valid_manifest)
        errors = validator.validate_normalize()

        assert len(errors) == 1

    def test_validate_tags_invalid_length(self, valid_manifest):
        valid_manifest['tags'].append('sm')
        validator = ManifestValidator(valid_manifest)
        errors = validator.validate_normalize()

        assert len(errors) == 2
        assert errors[1].startswith('Invalid tag')

    def test_validate_tags_invalid_symbols(self, valid_manifest):
        valid_manifest['tags'].append('wrOng t@g')
        validator = ManifestValidator(valid_manifest)
        errors = validator.validate_normalize()

        assert len(errors) == 2
        assert errors[1].startswith('Invalid tag')

    def test_validate_tags_duplicates(self, valid_manifest):
        valid_manifest['tags'].append('dup_tag')
        valid_manifest['tags'].append('duP_TaG')
        validator = ManifestValidator(valid_manifest)
        errors = validator.validate_normalize()

        assert len(errors) == 1
        assert errors[0].startswith('Some tags are more than once in the manifest')

    def test_validate_optional_dependency_success(self, valid_optional_dependency_manifest, monkeypatch):
        validator = ManifestValidator(valid_optional_dependency_manifest)
        errors = validator.validate_normalize()

        assert not errors

    @pytest.mark.parametrize(
        'invalid_str, error_message', [
            ('foo >= 4.4', 'Invalid if clause'),
            ('target is esp32', 'Invalid if clause'),
        ])
    def test_validate_optional_dependency_invalid_base(
            self, valid_optional_dependency_manifest, invalid_str, error_message):
        valid_optional_dependency_manifest['dependencies']['optional']['rules'][0]['if'] = invalid_str
        validator = ManifestValidator(valid_optional_dependency_manifest)
        errors = validator.validate_normalize()

        assert len(errors) == 4
        assert errors[-1].startswith(error_message)

    @pytest.mark.parametrize(
        'invalid_str, error_message', [
            ('idf_version >= 4.4!@#', 'Invalid simple block'),
            ('idf_version >= 4.4, <= "3.3"', 'Invalid simple block'),
        ])
    def test_validate_optional_dependency_invalid_derived(
            self, valid_optional_dependency_manifest, invalid_str, error_message):
        valid_optional_dependency_manifest['dependencies']['optional']['rules'][0]['if'] = invalid_str
        validator = ManifestValidator(valid_optional_dependency_manifest)
        errors = validator.validate_normalize()

        assert len(errors) == 5
        assert errors[-2].startswith(error_message)
        assert errors[-1].startswith('Invalid if clause')

    def test_known_targets_env(self, monkeypatch):
        monkeypatch.setenv(
            'IDF_COMPONENT_MANAGER_KNOWN_TARGETS', 'esp32,test,esp32s2,esp32s3,esp32c3,esp32h2,linux,esp32c2')
        result = known_targets()

        assert len(result) == 8
        assert 'test' in result

    def test_known_targets_idf(self, monkeypatch):
        monkeypatch.delenv('IDF_COMPONENT_MANAGER_KNOWN_TARGETS', raising=False)
        monkeypatch.setenv(
            'IDF_PATH', os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'fixtures', 'fake_idf'))
        result = known_targets()

        assert len(result) == 8
        assert 'test' in result

    def test_known_targets_default(self, monkeypatch):
        monkeypatch.delenv('IDF_COMPONENT_MANAGER_KNOWN_TARGETS', raising=False)
        monkeypatch.delenv('IDF_PATH', raising=False)
        result = known_targets()

        assert result == DEFAULT_KNOWN_TARGETS

    def test_no_unused_components(self, tmp_managed_components):
        project_requirements = [
            SolvedComponent(name='example/cmp', version=ComponentVersion('*'), source=LocalSource({'path': 'test'})),
            SolvedComponent(name='mag3110', version=ComponentVersion('*'), source=LocalSource({'path': 'test'}))
        ]
        detect_unused_components(project_requirements, tmp_managed_components)

        assert len(os.listdir(tmp_managed_components)) == 2

    def test_one_unused_component(self, tmp_managed_components):
        project_requirements = [
            SolvedComponent(name='mag3110', version=ComponentVersion('*'), source=LocalSource({'path': 'test'}))
        ]
        detect_unused_components(project_requirements, tmp_managed_components)

        assert len(os.listdir(tmp_managed_components)) == 1

    def test_all_unused_components(self, tmp_managed_components):
        project_requirements = []
        detect_unused_components(project_requirements, tmp_managed_components)

        assert not os.listdir(tmp_managed_components)

    def test_unused_files_message(self, tmp_path, capsys):
        managed_components_path = tmp_path / 'managed_components'
        managed_components_path.mkdir()

        unused_file = managed_components_path / 'unused_file'
        unused_file.write_text(u'test')

        project_requirements = []
        detect_unused_components(project_requirements, str(managed_components_path))
        captured = capsys.readouterr()

        assert 'Content of the managed components directory is managed automatically' in captured.err

    @pytest.mark.parametrize(
        'if_clause, bool_value', [
            ('idf_version > 4.4', True),
            ('idf_version <= "4.4"', False),
            ('idf_version >= 3.3, <=2.0', False),
            ('idf_version == 5.0.0', True),
            ('target == esp32', True),
            ('target != "esp32"', False),
            ('target in esp32', True),
            ('target in [esp32]', True),
            ('target in [esp32, "esp32c3"]', True),
            ('target in ["esp32s2", "esp32c3"]', False),
            ('target not in ["esp32s2", "esp32c3"]', True),
            ('target not in [esp32, esp32c3]', False),
        ])
    def test_parse_if_clause(self, if_clause, bool_value, monkeypatch):
        monkeypatch.setenv('IDF_VERSION', '5.0.0')
        monkeypatch.setenv('IDF_TARGET', 'esp32')

        assert parse_if_clause(if_clause).bool_value == bool_value
