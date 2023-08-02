# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import filecmp
import json
import os
import re
import warnings

import jsonschema
import pytest
import yaml

from idf_component_manager.dependencies import detect_unused_components
from idf_component_tools.errors import ManifestError
from idf_component_tools.manifest import (
    JSON_SCHEMA,
    SLUG_REGEX,
    ComponentVersion,
    ManifestManager,
    ManifestValidator,
    SolvedComponent,
)
from idf_component_tools.manifest.constants import DEFAULT_KNOWN_TARGETS, known_targets
from idf_component_tools.manifest.if_parser import OptionalDependency, parse_if_clause
from idf_component_tools.manifest.manifest import OptionalRequirement
from idf_component_tools.messages import MetadataKeyWarning
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

        assert parser.path == os.path.join(path, 'idf_component.yml')

    def test_parse_invalid_yaml(self, fixtures_path):
        manifest_path = os.path.join(fixtures_path, 'invalid_yaml.yml')
        parser = ManifestManager(manifest_path, name='fixtures')

        with pytest.raises(ManifestError) as e:
            parser.manifest_tree

        assert e.type == ManifestError
        assert str(e.value).startswith('Cannot parse')

    def test_parse_valid_yaml(self, capsys, fixtures_path):
        manifest_path = os.path.join(fixtures_path, 'idf_component.yml')
        parser = ManifestManager(manifest_path, name='fixtures')

        assert len(parser.manifest_tree.keys()) == 7

    def test_prepare(self, fixtures_path):
        manifest_path = os.path.join(fixtures_path, 'idf_component.yml')
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

    def test_env_var_with_escaped_dollar_sign(self, valid_manifest, tmp_path):
        valid_manifest['description'] = '$$foo$$$$$$bar'
        manifest_path = os.path.join(str(tmp_path), 'idf_component.yml')
        with open(manifest_path, 'w') as fw:
            yaml.dump(valid_manifest, fw)

        test_dump_path = os.path.join(str(tmp_path), 'test')
        os.mkdir(test_dump_path)

        parser = ManifestManager(manifest_path, name='test')
        parser.dump(str(test_dump_path))

        assert filecmp.cmp(
            manifest_path, os.path.join(test_dump_path, 'idf_component.yml'), shallow=False
        )

    def test_env_var_not_specified(self, valid_manifest, monkeypatch, tmp_path):
        valid_manifest['targets'] = ['$SUPPORT_TARGET']

        manifest_path = os.path.join(str(tmp_path), 'idf_component.yml')
        with open(manifest_path, 'w') as fw:
            yaml.dump(valid_manifest, fw)

        parser = ManifestManager(manifest_path, name='test')
        with pytest.raises(ManifestError, match='"SUPPORT_TARGET".*not set'):
            parser.load()


class TestManifestValidator(object):
    def test_validate_unknown_root_key(self, valid_manifest, recwarn):
        # unknown root keys
        valid_manifest['unknown'] = 'test'
        valid_manifest['test'] = 3.1415926

        # known root keys, but unknown subkeys
        valid_manifest['maintainers'] = {}
        valid_manifest['maintainers']['foo'] = 'bar'

        validator = ManifestValidator(valid_manifest)

        errors = validator.validate_normalize()
        assert len(errors) == 0
        assert len(recwarn) == 2

        # manifest_tree is not sorted. compare set not list
        assert set(warning.message.args[0] for warning in recwarn) == {
            'Unknown string field "foo" in the manifest file',
            'Dropping key "maintainers" from manifest.',
        }

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
            'test': {'version': '1.2.3'},
            'pest': {'version': '3.2.1'},
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
        assert errors[0].startswith('List of dependencies should be a dictionary')

    def test_validate_component_versions_unknown_key(self, valid_manifest):
        valid_manifest['dependencies'] = {
            'test-component': {'version': '^1.2.3', 'persion': 'asdf'}
        }
        validator = ManifestValidator(valid_manifest)

        errors = validator.validate_normalize()

        assert len(errors) == 5
        assert (
            errors[0]
            == 'Unknown string field "persion" in the manifest file that may affect build result'
        )
        assert errors[-1] == 'Unknown keys in dependency "test-component" details: persion'

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

        assert not errors

        validator.check_required_fields = True
        errors = validator.validate_normalize()

        assert len(errors) == 1
        assert errors[-1].startswith('Unknown targets: esp123, asdf')

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

        assert len(errors) == 2
        assert (
            errors[0]
            == 'Unknown number field "include" in the manifest file that may affect build result'
        )

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

    @pytest.mark.parametrize(
        'key, value',
        [
            ('targets', 'esp32'),
            ('maintainers', 'foo@bar.com'),
            ('tags', 'foobar'),
            ('include', '*.md'),
            ('exclude', '*.md'),
        ],
    )
    def test_validate_duplicates(self, valid_manifest, key, value):
        if key in ['include', 'exclude']:
            valid_manifest['files'][key].append(value)
            valid_manifest['files'][key].append(value.upper())
        elif key == 'targets':
            # can't use upper case
            valid_manifest[key].append(value)
            valid_manifest[key].append(value)
        else:
            valid_manifest[key].append(value)
            valid_manifest[key].append(value.upper())

        validator = ManifestValidator(valid_manifest)
        errors = validator.validate_normalize()

        assert len(errors) == 1
        assert errors[0].startswith('Duplicate item in "{}":'.format(key))
        assert value in errors[0]

    def test_validate_optional_dependency_success(
        self, valid_optional_dependency_manifest_with_idf, monkeypatch
    ):
        validator = ManifestValidator(valid_optional_dependency_manifest_with_idf)
        errors = validator.validate_normalize()

        assert not errors

    @pytest.mark.parametrize(
        'invalid_str, error_message',
        [
            ('foo >= 4.4', 'Invalid if clause'),
            ('target is esp32', 'Invalid if clause'),
        ],
    )
    def test_validate_optional_dependency_invalid_base(
        self, valid_optional_dependency_manifest_with_idf, invalid_str, error_message
    ):
        valid_optional_dependency_manifest_with_idf['dependencies']['optional']['rules'][0][
            'if'
        ] = invalid_str
        validator = ManifestValidator(valid_optional_dependency_manifest_with_idf)
        errors = validator.validate_normalize()

        assert len(errors) == 4
        assert errors[-1].startswith(error_message)

    @pytest.mark.parametrize(
        'invalid_str, error_message',
        [
            ('idf_version >= 4.4!@#', 'Dependency version spec format is invalid'),
            ('idf_version >= 4.4, <= "3.3"', 'Dependency version spec format is invalid'),
        ],
    )
    def test_validate_optional_dependency_invalid_derived(
        self, valid_optional_dependency_manifest_with_idf, invalid_str, error_message
    ):
        valid_optional_dependency_manifest_with_idf['dependencies']['optional']['rules'][0][
            'if'
        ] = invalid_str
        validator = ManifestValidator(valid_optional_dependency_manifest_with_idf)
        errors = validator.validate_normalize()

        assert len(errors) == 4
        assert errors[-2].startswith(error_message)
        assert errors[-1].startswith('Invalid version specification')

    def test_known_targets_env(self, monkeypatch):
        monkeypatch.setenv(
            'IDF_COMPONENT_MANAGER_KNOWN_TARGETS',
            'esp32,test,esp32s2,esp32s3,esp32c3,esp32h4,linux,esp32c2',
        )
        result = known_targets()

        assert len(result) == 8
        assert 'test' in result

    def test_known_targets_idf(self, monkeypatch, fixtures_path):
        monkeypatch.delenv('IDF_COMPONENT_MANAGER_KNOWN_TARGETS', raising=False)
        monkeypatch.setenv('IDF_PATH', os.path.join(fixtures_path, 'fake_idf'))
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
            SolvedComponent(
                name='example/cmp',
                version=ComponentVersion('*'),
                source=LocalSource({'path': 'test'}),
            ),
            SolvedComponent(
                name='mag3110', version=ComponentVersion('*'), source=LocalSource({'path': 'test'})
            ),
        ]
        detect_unused_components(project_requirements, tmp_managed_components)

        assert len(os.listdir(tmp_managed_components)) == 2

    def test_one_unused_component(self, tmp_managed_components):
        project_requirements = [
            SolvedComponent(
                name='mag3110', version=ComponentVersion('*'), source=LocalSource({'path': 'test'})
            )
        ]
        detect_unused_components(project_requirements, tmp_managed_components)

        assert len(os.listdir(tmp_managed_components)) == 1

    def test_all_unused_components(self, tmp_managed_components):
        project_requirements = []
        detect_unused_components(project_requirements, tmp_managed_components)

        assert not os.listdir(tmp_managed_components)

    def test_unused_files_message(self, tmp_path):
        managed_components_path = tmp_path / 'managed_components'
        managed_components_path.mkdir()

        unused_file = managed_components_path / 'unused_file'
        unused_file.write_text(u'test')

        project_requirements = []
        with warnings.catch_warnings(record=True) as w:
            detect_unused_components(project_requirements, str(managed_components_path))
            assert len(w) == 1
            assert issubclass(w[-1].category, UserWarning)
            assert 'Content of the managed components directory is managed automatically' in str(
                w[-1].message
            )

    def test_env_ignore_unknown_files_empty(self, monkeypatch, tmp_path):
        monkeypatch.setenv('IGNORE_UNKNOWN_FILES_FOR_MANAGED_COMPONENTS', '')
        managed_components_path = tmp_path / 'managed_components'
        managed_components_path.mkdir()

        unused_file = managed_components_path / 'unused_file'
        unused_file.write_text(u'test')

        with pytest.warns(UserWarning, match='1 unexpected files and directories were found*'):
            detect_unused_components([], str(managed_components_path))

    @pytest.mark.parametrize(
        'if_clause, bool_value',
        [
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
            ('target not in [esp32, esp32c3] || idf_version == 5.0.0', True),
            ('target not in [esp32, esp32c3] && idf_version == 5.0.0', False),
            ('(target in [esp32, esp32c3] || idf_version == 5.0.0) && idf_version == 6.0.0', False),
            ('target in [esp32, esp32c3] || (idf_version == 5.0.0 && idf_version == 6.0.0)', True),
        ],
    )
    def test_parse_if_clause(self, if_clause, bool_value, monkeypatch):
        monkeypatch.setenv('IDF_VERSION', '5.0.0')
        monkeypatch.setenv('IDF_TARGET', 'esp32')

        assert parse_if_clause(if_clause).bool_value == bool_value

    def test_validate_require_public_fields(self, valid_manifest):
        valid_manifest['dependencies']['test-8']['require'] = 'public'
        validator = ManifestValidator(valid_manifest)

        errors = validator.validate_normalize()

        assert len(errors) == 1
        assert 'require' in errors[0]

    def test_validate_links_wrong_url(self, valid_manifest):
        valid_manifest['issues'] = 'test.com/tracker'

        validator = ManifestValidator(valid_manifest)
        validator.validate_normalize()

        assert len(validator._errors) == 2

    def test_validate_links_wrong_git(self, valid_manifest):
        valid_manifest['repository'] = 'nogit@github.com:test_project/test.git'

        validator = ManifestValidator(valid_manifest)
        validator.validate_normalize()

        assert len(validator._errors) == 2

    def test_validate_examples_empty_element(self, valid_manifest):
        valid_manifest['examples'] = [{'path, test'}]  # list of set of string
        validator = ManifestValidator(valid_manifest)

        with pytest.warns(
            MetadataKeyWarning,
            match='Unknown array of array of string field "examples" in the manifest file',
        ):
            validator.validate_normalize()

        assert len(validator._errors) == 0

    def test_validate_rules_without_idf(self, valid_optional_dependency_manifest, monkeypatch):
        validator = ManifestValidator(valid_optional_dependency_manifest)
        errors = validator.validate_normalize()

        assert not errors

    def test_matches_with_versions(self, monkeypatch):
        req = OptionalRequirement(
            matches=[
                OptionalDependency('idf_version < 4.4', '1.0.0'),
                OptionalDependency('idf_version == 4.4.0'),
            ]
        )
        monkeypatch.setenv('IDF_VERSION', '5.0.0')
        assert req.version_spec_if_meet_conditions('*') is None

        monkeypatch.setenv('IDF_VERSION', '4.4.0')
        assert req.version_spec_if_meet_conditions('*') == '*'

        monkeypatch.setenv('IDF_VERSION', '3.0.0')
        assert req.version_spec_if_meet_conditions('*') == '1.0.0'

    def test_matches_with_rules(self, monkeypatch):
        req = OptionalRequirement(
            rules=[
                OptionalDependency('idf_version < 4.4', '1.0.0'),
                OptionalDependency('target == esp32', '1.0.1'),  # shall override
            ]
        )
        monkeypatch.setenv('IDF_VERSION', '5.0.0')
        monkeypatch.setenv('IDF_TARGET', 'esp32')
        assert req.version_spec_if_meet_conditions('*') is None

        monkeypatch.setenv('IDF_VERSION', '3.0.0')
        assert req.version_spec_if_meet_conditions('*') == '1.0.1'

    def test_rules_override_matches(self, monkeypatch):
        req = OptionalRequirement(
            matches=[
                OptionalDependency('idf_version < 4.4', '1.0.0'),
                OptionalDependency('idf_version == 4.4.0'),
            ],
            rules=[
                OptionalDependency('target == esp32', '1.0.3'),  # shall override
            ],
        )
        monkeypatch.setenv('IDF_VERSION', '5.0.0')
        monkeypatch.setenv('IDF_TARGET', 'esp32s2')
        assert req.version_spec_if_meet_conditions('*') is None

        monkeypatch.setenv('IDF_TARGET', 'esp32')
        assert req.version_spec_if_meet_conditions('*') is None

        monkeypatch.setenv('IDF_VERSION', '3.0.0')
        assert req.version_spec_if_meet_conditions('*') == '1.0.3'


def test_json_schema():
    schema_str = json.dumps(JSON_SCHEMA)

    try:
        validator = jsonschema.Draft7Validator
    except AttributeError:
        validator = jsonschema.Draft4Validator  # python 3.4

    validator.check_schema(json.loads(schema_str))
