# SPDX-FileCopyrightText: 2022 Espressif Systems (Shanghai) CO LTD
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
        'dependencies': {
            'dep1': [],
            'dep2': 4
        },
    }
    errors = ManifestValidator(manifest).validate_normalize()
    assert len(errors) == 5


def test_validator_valid_manifest(valid_manifest):
    assert not ManifestValidator(valid_manifest).validate_normalize()


def test_validator_passed_version(valid_manifest):
    errors = ManifestValidator(valid_manifest, version='5.0.0').validate_normalize()
    assert len(errors) == 1
    assert 'Manifest version (2.3.1~2) does not match the version specified in the command line (5.0.0).' in errors[0]


@pytest.mark.parametrize(
    'require_field,public,require', [
        ('public', True, True),
        ('private', False, True),
        ('no', None, False),
        (False, None, False),
        (None, None, True),
    ])
def test_require_field_public(require_field, public, require):
    test_manifest = {'dependencies': {'test': {'version': '*', 'require': require_field}}}
    manifest = Manifest.fromdict(test_manifest, name='test')

    assert manifest.dependencies[0].public is public
    assert manifest.dependencies[0].require is require
