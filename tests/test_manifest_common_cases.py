# SPDX-FileCopyrightText: 2022-2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os
import shutil
import typing as t
from copy import deepcopy
from pathlib import Path

import pytest

from idf_component_manager.core_utils import validate_examples_manifest
from idf_component_tools.errors import ManifestError
from idf_component_tools.manifest import ComponentRequirement, Manifest, OptionalDependency


def dep_by_name(manifest: Manifest, name: str) -> t.Optional[ComponentRequirement]:
    for dep in manifest.raw_requirements:
        if dep.name == name:
            return dep

    return None


def test_manifest_hash(valid_manifest):
    manifest = Manifest.fromdict(valid_manifest)
    # ONLY UPDATE MANIFEST HASH WHEN IT'S NECESSARY!!!
    assert (
        manifest.manifest_hash
        == '8dd1abf83989a97bcd7590b795f5436169f3a2d74a99c832cb97a2d3e8b44205'  # pragma: allowlist secret
    )


def test_project_manifest_builder(valid_manifest):
    manifest = Manifest.fromdict(valid_manifest)
    assert str(manifest.version) == '2.3.1~2'
    assert manifest.description == 'Test project'
    assert len(manifest.dependencies) == 8
    assert manifest.targets == ['esp32']
    test1 = dep_by_name(manifest, 'espressif/test-1')
    assert test1.version == '^1.2.7'
    assert not test1.is_public
    test8 = dep_by_name(manifest, 'espressif/test-8')
    assert test8.is_public
    assert dep_by_name(manifest, 'espressif/test-2').version == '*'
    assert dep_by_name(manifest, 'espressif/test-4').version == '*'
    assert manifest.links.url == 'https://test.com/homepage'
    assert manifest.links.documentation == 'https://test.com/documentation'
    assert manifest.links.repository == 'git@github.com:test_project/test.git'
    assert manifest.links.issues == 'https://test.com/tracker'
    assert manifest.links.discussion == 'https://discuss.com/discuss'


def test_project_manifest_builder_with_overrides():
    manifest = Manifest.fromdict({
        'dependencies': {'espressif/esp_tinyusb': '~1.7.6'},
        'overrides': [
            {
                'espressif/tinyusb': {
                    'with': {
                        'my_tinyusb': {
                            'git': 'https://github.com/micropython/tinyusb-espressif.git',
                            'path': '.',
                            'version': 'cherrypick/dwc2_zlp_fix',
                        }
                    }
                }
            }
        ],
    })

    assert len(manifest.overrides) == 1
    override_item = manifest.overrides[0]
    assert override_item.target == 'espressif/tinyusb'
    assert override_item.replacement_name == 'my_tinyusb'
    assert (
        override_item.with_dependency.git == 'https://github.com/micropython/tinyusb-espressif.git'
    )
    assert override_item.with_dependency.path == '.'
    assert override_item.with_dependency.version == 'cherrypick/dwc2_zlp_fix'


def test_project_manifest_builder_with_overrides_short_name_normalized():
    manifest = Manifest.fromdict({
        'overrides': [
            {
                'tinyusb': {
                    'with': {
                        'my_tinyusb': {
                            'git': 'https://github.com/micropython/tinyusb-espressif.git',
                            'path': '.',
                            'version': 'cherrypick/dwc2_zlp_fix',
                        }
                    }
                }
            }
        ],
    })

    assert manifest.overrides[0].target == 'espressif/tinyusb'
    assert manifest.overrides[0].replacement_name == 'my_tinyusb'
    assert manifest.overrides[0].with_dependency.version == 'cherrypick/dwc2_zlp_fix'


def test_validator_broken_deps():
    manifest = {
        'dependencies': {'dep1': [], 'dep2': 4},
    }
    errors = Manifest.validate_manifest(manifest)

    assert errors == [
        'Invalid field "dependencies:dep1": Supported types for "dependency" field: "str,dict"',
        'Invalid field "dependencies:dep2": Supported types for "dependency" field: "str,dict"',
    ]


def test_validator_valid_manifest(valid_manifest):
    assert not Manifest.validate_manifest(valid_manifest)


def test_validator_invalid_override_name():
    manifest = {
        'overrides': [
            {
                'invalid_slug---': {
                    'with': {
                        'my_tinyusb': {
                            'git': 'https://github.com/micropython/tinyusb-espressif.git',
                            'path': '.',
                            'version': 'cherrypick/dwc2_zlp_fix',
                        }
                    }
                }
            }
        ]
    }

    errors = Manifest.validate_manifest(manifest)

    assert errors == ['Invalid field "overrides:invalid_slug---": Invalid component name']


def test_validator_invalid_override_git_version_spec():
    manifest = {
        'overrides': [
            {
                'tinyusb': {
                    'with': {
                        'my_tinyusb': {
                            'git': 'https://github.com/micropython/tinyusb-espressif.git',
                            'path': '.',
                            'version': 'invalid ref with spaces',
                        }
                    }
                }
            }
        ]
    }

    errors = Manifest.validate_manifest(manifest)

    assert errors == [
        'Invalid field "overrides:tinyusb:with:my_tinyusb:version": Invalid version specification "invalid ref with spaces"'
    ]


@pytest.mark.parametrize(
    ('overrides', 'errors'),
    [
        ({}, ['Invalid field "overrides": Input should be a valid array']),
        ('', ['Invalid field "overrides": Input should be a valid array']),
        (
            [{'joltwallet/littlefs': 'foo'}],
            ['Invalid field "overrides:joltwallet/littlefs": Input should be a valid dictionary'],
        ),
        (
            [{'joltwallet/littlefs': {'with': 'foo'}}],
            [
                'Invalid field "overrides:joltwallet/littlefs:with": Input should be a valid dictionary'
            ],
        ),
        (
            [{'joltwallet/littlefs': {'with': {'joltwallet/littlefs': 'foo'}}}],
            [
                'Invalid field "overrides:joltwallet/littlefs:with:joltwallet/littlefs": Input should be a valid dictionary'
            ],
        ),
    ],
)
def test_validator_malformed_overrides(overrides, errors):
    assert Manifest.validate_manifest({'overrides': overrides}) == errors


def test_manifest_hash_changes_when_overrides_change():
    manifest_a = Manifest.fromdict({
        'dependencies': {'espressif/esp_tinyusb': '~1.7.6'},
        'overrides': [
            {
                'tinyusb': {
                    'with': {
                        'my_tinyusb': {
                            'git': 'https://github.com/micropython/tinyusb-espressif.git',
                            'path': '.',
                            'version': 'cherrypick/dwc2_zlp_fix',
                        }
                    }
                }
            }
        ],
    })
    manifest_b = Manifest.fromdict({
        'dependencies': {'espressif/esp_tinyusb': '~1.7.6'},
        'overrides': [
            {
                'tinyusb': {
                    'with': {
                        'my_tinyusb': {
                            'git': 'https://github.com/micropython/tinyusb-espressif.git',
                            'path': '.',
                            'version': 'another_fix_branch',
                        }
                    }
                }
            }
        ],
    })

    assert manifest_a.manifest_hash != manifest_b.manifest_hash


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
                    'espressif/cbor': {
                        'version': '~0.6',
                        'rules': [{'if': 'idf_version >=5.0'}],
                    },
                    'invalid_slug---': {
                        'version': '~0.6',
                    },
                },
            },
            [
                'Invalid field "dependencies:espressif/esp_diag_data_store:service_url": String should have at least 1 character',
            ],
        ),
        (
            {
                'version': '1.0.0',
                'description': None,
                'url': 'https://github.com/espressif/esp-insights/tree/main/components/esp_insights',
            },
            ['Invalid field "description": Input should be a valid string'],
        ),
        (
            'str',
            ['Invalid manifest format. Manifest should be a dictionary'],
        ),
    ],
)
def test_invalid_manifest(manifest, errors):
    produced_errors = Manifest.validate_manifest(manifest)
    for error in errors:
        assert error in produced_errors


def test_validator_repo_info_and_repo(valid_manifest):
    original_valid_manifest = deepcopy(valid_manifest)

    valid_manifest['repository_info'] = {
        'commit_sha': '252f10c83610ebca1a059c0bae8255eba2f95be4d1d7bcfa89d7248a82d9f111'  # pragma: allowlist secret
    }
    del valid_manifest['repository']
    errors = Manifest.validate_manifest(valid_manifest)
    assert errors == [
        'Invalid field "repository". Must set when "repository_info" is set',
    ]

    valid_manifest = deepcopy(original_valid_manifest)
    valid_manifest['repository_info'] = {'path': 'foo/bar'}
    del valid_manifest['repository']
    errors = Manifest.validate_manifest(valid_manifest)
    assert errors == [
        'Invalid field "repository". Must set when "repository_info" is set',
    ]

    valid_manifest = deepcopy(original_valid_manifest)
    valid_manifest['repository_info'] = {}
    del valid_manifest['repository']
    errors = Manifest.validate_manifest(valid_manifest)
    assert errors == [
        'Invalid field "repository". Must set when "repository_info" is set',
    ]

    valid_manifest = deepcopy(original_valid_manifest)
    valid_manifest.pop('repository_info', None)
    del valid_manifest['repository']
    errors = Manifest.validate_manifest(valid_manifest)
    assert errors == []


@pytest.mark.parametrize(
    'require_field,public,require',
    [
        ('public', True, True),
        ('private', False, True),
        ('no', False, False),
        (False, False, False),
    ],
)
def test_require_field_public(require_field, public, require):
    test_manifest = {'dependencies': {'test': {'version': '*', 'require': require_field}}}
    manifest = Manifest.fromdict(test_manifest)

    assert manifest.requirements[0].is_public is public
    assert manifest.requirements[0].is_required is require


def test_meet_optional_dependency_with_none_version_requirement(monkeypatch):
    monkeypatch.setenv('IDF_TARGET', 'esp32c6')

    req = ComponentRequirement(
        name='foo',
        path='/test/',
        rules=[
            OptionalDependency.fromdict({'if': 'target in [esp32c6]'}),
        ],
    )

    assert req.meet_optional_dependencies
    assert req.version is None
    assert req.version_spec == '*'


def test_validate_example_manifest(cmp_with_example):
    validate_examples_manifest(cmp_with_example)


def test_validate_invalid_example_manifest(cmp_with_example, tmp_path):
    # Copy component with examples to a temporary directory for modification
    shutil.copytree(cmp_with_example, os.path.join(tmp_path, 'cmp_with_example'))

    # Create invalid example manifest
    Path(
        tmp_path,
        'cmp_with_example',
        'examples',
        'cmp_ex',
        'main',
        'idf_component.yml',
    ).write_text('...')

    with pytest.raises(ManifestError):
        validate_examples_manifest(os.path.join(tmp_path, 'cmp_with_example'))
