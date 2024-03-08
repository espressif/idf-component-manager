# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import pytest

from idf_component_tools.manifest import Manifest, ManifestValidator


def dep_by_name(manifest, name):
    for dependency in manifest.dependencies:
        if dependency.name == name:
            return dependency


def test_manifest_hash(valid_manifest, valid_manifest_hash):
    manifest = Manifest.fromdict(valid_manifest, name='test')
    assert manifest.manifest_hash == valid_manifest_hash


def test_project_manifest_builder(valid_manifest):
    manifest = Manifest.fromdict(valid_manifest, name='test')
    assert str(manifest.version) == '2.3.1~2'
    assert manifest.description == 'Test project'
    assert len(manifest.dependencies) == 8
    assert manifest.targets == ['esp32']
    test1 = dep_by_name(manifest, 'espressif/test-1')
    assert test1.version_spec == '^1.2.7'
    assert not test1.public
    test8 = dep_by_name(manifest, 'espressif/test-8')
    assert test8.public
    assert dep_by_name(manifest, 'espressif/test-2').version_spec == '*'
    assert dep_by_name(manifest, 'espressif/test-4').version_spec == '*'
    assert manifest.links.url == 'https://test.com/homepage'
    assert manifest.links.documentation == 'https://test.com/documentation'
    assert manifest.links.repository == 'git@github.com:test_project/test.git'
    assert manifest.links.issues == 'https://test.com/tracker'
    assert manifest.links.discussion == 'https://discuss.com/discuss'


def test_validator_broken_deps():
    manifest = {
        'dependencies': {'dep1': [], 'dep2': 4},
    }
    errors = ManifestValidator(manifest).validate_normalize()
    assert len(errors) == 6
    assert (
        errors[0]
        == 'Unknown number field "dependencies:*" in the manifest file that may affect build result'
    )


def test_validator_valid_manifest(valid_manifest):
    assert not ManifestValidator(valid_manifest).validate_normalize()


@pytest.mark.parametrize(
    ('manifest', 'errors'),
    [
        (
            {
                'version': '1.0.0',
                'description': 'Some description',
                'url': 'https://github.com/espressif/esp-insights/tree/main/components/esp_insights',
                'dependencies': {
                    'espressif/rmaker_common': {
                        'version': '~1.4.0',
                        'override_path': '../rmaker/common/',
                    },
                    'espressif/esp_diag_data_store': {
                        'version': '.1.0',
                        'override_path': '../esp_diag_data_store/',
                        'service_url': '',
                    },
                    'espressif/esp_diagnostics': {
                        'version': '.1.0',
                        'override_path': '../esp_diagnostics/',
                    },
                    'espressif/cbor': {'version': '~0.6', 'rules': [{'if': 'idf_version >=5.0'}]},
                    'invalid_slug---': {
                        'version': '~0.6',
                    },
                },
            },
            [
                'Non-empty string is required in the "service_url" field',
                'Version specifications for "espressif/esp_diagnostics" are invalid.',
                'Component\'s name is not valid "invalid_slug---", should contain only letters, numbers, /, _ and -.',
            ],
        ),
        (
            {
                'version': '1.0.0',
                'description': None,
                'url': 'https://github.com/espressif/esp-insights/tree/main/components/esp_insights',
            },
            ['Invalid manifest format', 'Non-empty string is required in the "description" field'],
        ),
    ],
)
def test_invalid_manifest(manifest, errors):
    produced_errors = ManifestValidator(manifest).validate_normalize()
    for error in errors:
        assert error in produced_errors


def test_validator_commit_sha_and_repo(valid_manifest):
    valid_manifest['commit_sha'] = (
        '252f10c83610ebca1a059c0bae8255eba2f95be4d1d7bcfa89d7248a82d9f111'
    )
    del valid_manifest['repository']

    errors = ManifestValidator(valid_manifest, check_required_fields=True).validate_normalize()
    assert len(errors) == 1
    assert 'The `repository` field is required in the `idf_component.yml` file when' in errors[0]


@pytest.mark.parametrize(
    'require_field,public,require',
    [
        ('public', True, True),
        ('private', False, True),
        ('no', None, False),
        (False, None, False),
        (None, None, True),
    ],
)
def test_require_field_public(require_field, public, require):
    test_manifest = {'dependencies': {'test': {'version': '*', 'require': require_field}}}
    manifest = Manifest.fromdict(test_manifest, name='test')

    assert manifest.dependencies[0].public is public
    assert manifest.dependencies[0].require is require
