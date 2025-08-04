# SPDX-FileCopyrightText: 2023-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import logging
import os
import re

import pytest

from idf_component_manager.dependencies import detect_unused_components
from idf_component_tools import LOGGING_NAMESPACE
from idf_component_tools.debugger import KCONFIG_CONTEXT
from idf_component_tools.manager import ManifestManager, UploadMode
from idf_component_tools.manifest import SLUG_REGEX, OptionalRequirement, SolvedComponent
from idf_component_tools.manifest.constants import DEFAULT_KNOWN_TARGETS, known_targets
from idf_component_tools.manifest.if_parser import parse_if_clause
from idf_component_tools.manifest.models import Manifest, OptionalDependency
from idf_component_tools.sources import LocalSource
from idf_component_tools.utils import ComponentVersion, validation_context


class TestManifestValidator:
    def test_validate_unknown_root_key(self, valid_manifest, caplog):
        # unknown root keys
        valid_manifest['unknown'] = 'test'
        valid_manifest['test'] = 3.1415926

        # known root keys, but unknown subkeys
        valid_manifest['repository_info'] = {}
        valid_manifest['repository_info']['foo'] = 'bar'

        with caplog.at_level(logging.DEBUG, logger=LOGGING_NAMESPACE):
            errors = Manifest.validate_manifest(valid_manifest)
            assert not errors

            assert len(caplog.records) == 3
            assert set([rec.message for rec in caplog.records]) == {
                'Dropping unknown key: foo=bar',
                'Dropping unknown key: unknown=test',
                'Dropping unknown key: test=3.1415926',
            }

    def test_validate_unknown_root_values(self, valid_manifest):
        valid_manifest['version'] = '1!.3.3'
        errors = Manifest.validate_manifest(valid_manifest)

        assert errors == ['Invalid field "version": Invalid version string: "1!.3.3"']

    def test_validate_component_versions_not_in_manifest(self, valid_manifest):
        valid_manifest.pop('dependencies')
        errors = Manifest.validate_manifest(valid_manifest)

        assert not errors

    def test_validate_dependencies_version_untouched(self, valid_manifest):
        valid_manifest['dependencies'] = {'test': '1.2.3', 'pest': {'version': '3.2.1'}}

        manifest = Manifest(**valid_manifest)

        assert manifest.model_dump()['dependencies'] == {
            'test': '1.2.3',
            'pest': {
                'version': '3.2.1',
            },
        }

    def test_validate_component_versions_are_empty(self, valid_manifest):
        valid_manifest['dependencies'] = {}
        errors = Manifest.validate_manifest(valid_manifest)

        assert not errors

    def test_validate_component_versions_not_a_dict(self, valid_manifest):
        valid_manifest['dependencies'] = ['one_component', 'another-one']
        errors = Manifest.validate_manifest(valid_manifest)

        assert errors == ['Invalid field "dependencies": Input should be a valid dictionary']

    def test_validate_component_versions_unknown_key(self, valid_manifest):
        valid_manifest['dependencies'] = {
            'test-component': {'version': '^1.2.3', 'foo': 'bar', 'bar': 'foo'}
        }
        errors = Manifest.validate_manifest(valid_manifest)

        assert errors == [
            'Invalid field "dependencies:test-component": Unknown fields "bar,foo" under "dependencies" field that may affect build result'
        ]

    def test_validate_component_versions_invalid_name(self, valid_manifest):
        valid_manifest['dependencies'] = {'asdf!fdsa': {'version': '^1.2.3'}}
        errors = Manifest.validate_manifest(valid_manifest)

        assert errors == ['Invalid field "dependencies:asdf!fdsa": Invalid component name']

    def test_validate_component_versions_invalid_spec_subkey(self, valid_manifest):
        valid_manifest['dependencies'] = {'test-component': {'version': '^1.2a.3'}}
        errors = Manifest.validate_manifest(valid_manifest)

        assert errors == [
            'Invalid field "dependencies:test-component:version": Invalid version specification "^1.2a.3"'
        ]

    def test_validate_component_versions_invalid_spec(self, valid_manifest):
        valid_manifest['dependencies'] = {'test-component': '~=1a.2.3'}
        errors = Manifest.validate_manifest(valid_manifest)

        assert errors == [
            'Invalid field "dependencies:test-component:version": Invalid version specification "~=1a.2.3"'
        ]

    def test_validate_targets_unknown(self, valid_manifest):
        valid_manifest['targets'] = ['esp123', 'esp32', 'asdf']
        errors = Manifest.validate_manifest(valid_manifest)

        assert not errors

        with validation_context({'upload_mode': UploadMode.component}):
            errors = Manifest.validate_manifest(valid_manifest)

        assert errors == ['Invalid field "targets". Unknown targets: "asdf,esp123"']

    @pytest.mark.parametrize(
        'name',
        [
            'asdf-fadsf',
            '123',
            'asdf_erw',
            'as_df_erw',
            'test-stse-sdf_sfd',
        ],
    )
    def test_slug_re_valid_names(self, name):
        assert re.match(SLUG_REGEX, name)

    @pytest.mark.parametrize(
        'name',
        [
            '!',
            'asdf$f',
            'daf411~',
            'adf\nadsf',
            '_',
            '-',
            '_good',
            'asdf-_-fdsa-',
            'asdf_-asdf',
            'asdf--asdf',
            'asdf__asdf',
            'asdf_-_asdf',
        ],
    )
    def test_slug_re_invalid_names(self, name):
        assert not re.match(SLUG_REGEX, name)

    def test_validate_version_list(self, valid_manifest):
        errors = Manifest.validate_manifest(valid_manifest)

        assert not errors

    def test_check_required_keys(self, valid_manifest):
        with validation_context({'upload_mode': UploadMode.component}):
            errors = Manifest.validate_manifest(valid_manifest)

        assert not errors

    def test_check_required_keys_empty_manifest(self):
        with validation_context({'upload_mode': UploadMode.component}):
            errors = Manifest.validate_manifest({})

        assert errors == [
            'Invalid field "version". Must set while uploading component to the registry'
        ]

    def test_validate_files_invalid_list(self, valid_manifest):
        valid_manifest['files']['include'] = 34
        errors = Manifest.validate_manifest(valid_manifest)

        assert errors == ['Invalid field "files:include": Input should be a valid list']

    @pytest.mark.parametrize(
        'invalid_tag',
        [
            'sm',
            'wrOng t@g',
        ],
    )
    def test_validate_invalid_tags(self, valid_manifest, invalid_tag):
        valid_manifest['tags'].append(invalid_tag)
        errors = Manifest.validate_manifest(valid_manifest)

        assert errors == [
            'Invalid field "tags:[3]": String should match pattern \'^[A-Za-z0-9\\_\\-]{3,32}$\''
        ]

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
            key = f'files:{key}'
        elif key == 'targets':
            # can't use upper case
            valid_manifest[key].append(value)
            valid_manifest[key].append(value)
        else:
            valid_manifest[key].append(value)
            valid_manifest[key].append(value.upper())

        errors = Manifest.validate_manifest(valid_manifest)

        assert errors == [f'Invalid field "{key}": List must be unique. Duplicate value: "{value}"']

    def test_known_targets_env(self, monkeypatch):
        monkeypatch.setenv(
            'IDF_COMPONENT_MANAGER_KNOWN_TARGETS',
            'esp32,test,esp32s2,esp32s3,esp32c3,esp32h4,linux,esp32c2',
        )
        result = known_targets()

        assert len(result) == 8
        assert 'test' in result

    def test_known_targets_idf(self, monkeypatch, fixtures_path):
        monkeypatch.setenv('IDF_PATH', os.path.join(fixtures_path, 'fake_idf'))
        result = known_targets()

        assert len(result) == 8
        assert 'test' in result

    def test_known_targets_default(self, monkeypatch):
        monkeypatch.delenv('IDF_PATH', raising=False)
        result = known_targets()

        assert result == DEFAULT_KNOWN_TARGETS

    def test_no_unused_components(self, tmp_managed_components):
        project_requirements = [
            SolvedComponent(
                name='example/cmp',
                version=ComponentVersion('*'),
                source=LocalSource(path='test'),
            ),
            SolvedComponent(
                name='mag3110', version=ComponentVersion('*'), source=LocalSource(path='test')
            ),
        ]
        detect_unused_components(project_requirements, tmp_managed_components)

        assert len(os.listdir(tmp_managed_components)) == 2

    def test_one_unused_component(self, tmp_managed_components):
        project_requirements = [
            SolvedComponent(
                name='mag3110', version=ComponentVersion('*'), source=LocalSource(path='test')
            )
        ]
        detect_unused_components(project_requirements, tmp_managed_components)

        assert len(os.listdir(tmp_managed_components)) == 1

    def test_all_unused_components(self, tmp_managed_components):
        project_requirements = []
        detect_unused_components(project_requirements, tmp_managed_components)

        assert not os.listdir(tmp_managed_components)

    def test_unused_files_message(self, tmp_path, caplog):
        managed_components_path = tmp_path / 'managed_components'
        managed_components_path.mkdir()

        unused_file = managed_components_path / 'unused_file'
        unused_file.write_text('test')

        project_requirements = []

        with caplog.at_level(logging.WARNING, logger=LOGGING_NAMESPACE):
            detect_unused_components(project_requirements, str(managed_components_path))
            assert len(caplog.records) == 1
            assert 'Content of the managed components directory is managed automatically' in str(
                caplog.records[0].message
            )

    def test_env_ignore_unknown_files_empty(self, monkeypatch, tmp_path, caplog):
        monkeypatch.setenv('IGNORE_UNKNOWN_FILES_FOR_MANAGED_COMPONENTS', '')
        managed_components_path = tmp_path / 'managed_components'
        managed_components_path.mkdir()

        unused_file = managed_components_path / 'unused_file'
        unused_file.write_text('test')

        with caplog.at_level(logging.WARNING, logger=LOGGING_NAMESPACE):
            detect_unused_components([], str(managed_components_path))
            assert len(caplog.records) == 1
            assert (
                'Content of the managed components directory is managed automatically'
                in caplog.records[0].message
            )

    @pytest.mark.parametrize(
        'if_clause, bool_value',
        [
            ('idf_version > 4.4', True),
            ('idf_version <= "4.4"', False),
            ('idf_version >= 3.3, <=2.0', False),
            ('idf_version == 5.0.0', True),
            ('target == esp32', True),
            ('target != "esp32"', False),
            ('target in [esp32]', True),
            ('target in [esp32, "esp32c3"]', True),
            ('target in ["esp32s2", "esp32c3"]', False),
            ('target not in ["esp32s2", "esp32c3"]', True),
            ('target not in [esp32, esp32c3]', False),
            ('target not in [esp32, esp32c3] || idf_version == 5.0.0', True),
            ('target not in [esp32, esp32c3] && idf_version == 5.0.0', False),
            ('(target in [esp32, esp32c3] || idf_version == 5.0.0) && idf_version == 6.0.0', False),
            ('target in [esp32, esp32c3] || (idf_version == 5.0.0 && idf_version == 6.0.0)', True),
            ('$CONFIG{integer_9} == 9', True),
            ('$CONFIG{integer_9} < 11', True),
            ('$CONFIG{integer_9} >= 9', True),
            ('$CONFIG{hex_1} == 0x1', True),
            ('$CONFIG{hex_1} <= 1', True),
            ('$CONFIG{bool_true} == True', True),
            ('$CONFIG{bool_false} == False', True),
            ('$CONFIG{string_foo} == "foo"', True),
            ('$CONFIG{string_foo} == foo', True),
            ('$CONFIG{version_4_0_0} == 4.0.0', True),
            ('$CONFIG{version_4_0_0} == 4.0', True),
        ],
    )
    def test_parse_if_clause(self, if_clause, bool_value, monkeypatch):
        monkeypatch.setenv('CI_TESTING_IDF_VERSION', '5.0.0')
        monkeypatch.setenv('IDF_TARGET', 'esp32')

        KCONFIG_CONTEXT.get().sdkconfig.update({
            'integer_9': 9,
            'hex_1': 0x1,
            'bool_true': True,
            'bool_false': False,
            'string_foo': 'foo',
            'version_4_0_0': '4.0.0',
        })

        assert parse_if_clause(if_clause).get_value() == bool_value

    def test_validate_require_public_fields(self, valid_manifest):
        valid_manifest['dependencies']['test-8']['require'] = 'public'
        errors = Manifest.validate_manifest(valid_manifest)

        assert errors == [
            'Invalid field "dependencies:test-8: "public" and "require" fields must not set at the same time'
        ]

    def test_validate_require_field_support_boolean_string(self, valid_manifest):
        valid_manifest['dependencies']['test']['require'] = 'public'
        errors = Manifest.validate_manifest(valid_manifest)

        assert not errors

        valid_manifest['dependencies']['test']['require'] = False
        errors = Manifest.validate_manifest(valid_manifest)

        assert not errors

    def test_validate_require_field_random_string_error(self, valid_manifest):
        valid_manifest['dependencies']['test']['require'] = 'random'
        errors = Manifest.validate_manifest(valid_manifest)

        assert errors == [
            "Invalid field \"dependencies:test:require\": Input should be 'public', 'private' or 'no'"
        ]

    def test_validate_require_field_true_error(self, valid_manifest):
        valid_manifest['dependencies']['test']['require'] = True
        errors = Manifest.validate_manifest(valid_manifest)

        assert len(errors) == 1
        assert errors == ['Invalid field "dependencies:test:require": Input should be False']

    def test_validate_links_wrong_url(self, valid_manifest):
        valid_manifest['issues'] = 'test.com/tracker'
        errors = Manifest.validate_manifest(valid_manifest)

        assert errors == [
            'Invalid field "issues": Input should be a valid URL, relative URL without a base'
        ]

    def test_validate_links_wrong_git(self, valid_manifest):
        valid_manifest['repository'] = 'nogit@github.com:test_project/test.git'
        errors = Manifest.validate_manifest(valid_manifest)

        assert errors == [
            'Invalid field "repository": Invalid git URL: nogit@github.com:test_project/test.git'
        ]

    def test_validate_rules_without_idf(
        self,
        valid_optional_dependency_manifest,
    ):
        errors = Manifest.validate_manifest(valid_optional_dependency_manifest)

        assert not errors

    def test_matches_with_versions(self, monkeypatch):
        req = OptionalRequirement(
            matches=[
                OptionalDependency.fromdict({'if': 'idf_version < 4.4', 'version': '1.0.0'}),
                OptionalDependency.fromdict({'if': 'idf_version == 4.4.0'}),
            ]
        )
        monkeypatch.setenv('CI_TESTING_IDF_VERSION', '5.0.0')
        assert req.version_spec_if_meet_conditions('*') is None

        monkeypatch.setenv('CI_TESTING_IDF_VERSION', '4.4.0')
        assert req.version_spec_if_meet_conditions('*') == '*'

        monkeypatch.setenv('CI_TESTING_IDF_VERSION', '3.0.0')
        assert req.version_spec_if_meet_conditions('*') == '1.0.0'

    def test_matches_with_rules(self, monkeypatch):
        req = OptionalRequirement(
            rules=[
                OptionalDependency.fromdict({'if': 'idf_version < 4.4', 'version': '1.0.0'}),
                OptionalDependency.fromdict({
                    'if': 'target == esp32',
                    'version': '1.0.1',
                }),  # shall override
            ]
        )
        monkeypatch.setenv('CI_TESTING_IDF_VERSION', '5.0.0')
        monkeypatch.setenv('IDF_TARGET', 'esp32')
        assert req.version_spec_if_meet_conditions('*') is None

        monkeypatch.setenv('CI_TESTING_IDF_VERSION', '3.0.0')
        assert req.version_spec_if_meet_conditions('*') == '1.0.1'

    def test_rules_override_matches(self, monkeypatch):
        req = OptionalRequirement(
            matches=[
                OptionalDependency.fromdict({'if': 'idf_version < 4.4', 'version': '1.0.0'}),
                OptionalDependency.fromdict({'if': 'idf_version == 4.4.0'}),
            ],
            rules=[
                OptionalDependency.fromdict({
                    'if': 'target == esp32',
                    'version': '1.0.3',
                }),  # shall override
            ],
        )
        monkeypatch.setenv('CI_TESTING_IDF_VERSION', '5.0.0')
        monkeypatch.setenv('IDF_TARGET', 'esp32s2')
        assert req.version_spec_if_meet_conditions('*') is None

        monkeypatch.setenv('IDF_TARGET', 'esp32')
        assert req.version_spec_if_meet_conditions('*') is None

        monkeypatch.setenv('CI_TESTING_IDF_VERSION', '3.0.0')
        assert req.version_spec_if_meet_conditions('*') == '1.0.3'

    def test_validate_optional_dependency_not_expanded_success(
        self, valid_optional_dependency_manifest_with_idf
    ):
        errors = Manifest.validate_manifest(valid_optional_dependency_manifest_with_idf)

        assert not errors


class TestManifestValidatorUploadMode:
    def test_validate_optional_dependency_success(
        self, valid_optional_dependency_manifest_with_idf
    ):
        with validation_context({'upload_mode': UploadMode.component}):
            errors = Manifest.validate_manifest(valid_optional_dependency_manifest_with_idf)

        assert not errors

    @pytest.mark.parametrize(
        'invalid_str, expected_errors',
        [
            (
                'foo >= 4.4',
                [
                    'Invalid field "dependencies:optional:rules:[0]:if": Invalid version string: "foo"'
                ],
            ),
            (
                'target is esp32',
                [
                    'Invalid field "dependencies:optional:rules:[0]:if": Invalid syntax: "target is esp32"'
                ],
            ),
        ],
    )
    def test_validate_optional_dependency_invalid(
        self, valid_optional_dependency_manifest_with_idf, invalid_str, expected_errors
    ):
        valid_optional_dependency_manifest_with_idf['dependencies']['optional']['rules'][0][
            'if'
        ] = invalid_str

        with validation_context({'upload_mode': UploadMode.component}):
            errors = Manifest.validate_manifest(valid_optional_dependency_manifest_with_idf)

        assert errors == expected_errors

    @pytest.mark.parametrize(
        'invalid_str, expected_errors',
        [
            (
                'idf_version >= 4.4!@#',
                [
                    'Invalid field "dependencies:optional:rules:[0]:if": Invalid version spec ">=4.4!@#"'
                ],
            ),
            (
                'idf_version >= 4.4, <= "3.3"',
                [
                    'Invalid field "dependencies:optional:rules:[0]:if": Invalid version spec ">=4.4,<="3.3""'
                ],
            ),
        ],
    )
    def test_validate_optional_dependency_invalid_derived(
        self, valid_optional_dependency_manifest_with_idf, invalid_str, expected_errors, monkeypatch
    ):
        monkeypatch.setenv('CI_TESTING_IDF_VERSION', '')
        valid_optional_dependency_manifest_with_idf['dependencies']['optional']['rules'][0][
            'if'
        ] = invalid_str
        with validation_context({'upload_mode': UploadMode.component}):
            errors = Manifest.validate_manifest(valid_optional_dependency_manifest_with_idf)

        assert errors == expected_errors


@pytest.mark.parametrize(
    'manifest_obj, error',
    [
        ('a string', 'Manifest file should be a dictionary.'),
        (None, None),
        ('version: 1.0.0', None),
    ],
)
def test_validate_manifest_file(tmp_path, manifest_obj, error):
    with open(tmp_path / 'idf_component.yml', 'w') as fw:
        if manifest_obj:
            fw.write(manifest_obj)

    manifest = ManifestManager(tmp_path, 'main').validate()
    if error:
        assert error in manifest.validation_errors[0]
    else:
        assert manifest.validation_errors == []
