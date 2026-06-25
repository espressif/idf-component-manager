# SPDX-FileCopyrightText: 2022-2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0


import jsonschema
import pytest

from idf_component_tools.errors import ManifestError
from idf_component_tools.manifest import MANIFEST_JSON_SCHEMA, Manifest
from idf_component_tools.utils import ProjectRequirements


def test_json_schema():
    validator = jsonschema.Draft7Validator
    validator.check_schema(MANIFEST_JSON_SCHEMA)


def test_json_schema_contains_overrides_definition():
    overrides = MANIFEST_JSON_SCHEMA['properties']['overrides']

    assert overrides['type'] == 'array'
    assert overrides['items']['$ref'] == '#/$defs/OverrideDefinition'
    assert 'override_path' not in MANIFEST_JSON_SCHEMA['$defs']['OverrideItem']['properties']


def test_project_requirements_collects_manifest_override_rules():
    manifest = Manifest.fromdict({
        'overrides': [
            {
                'tinyusb': {
                    'with': {
                        'my_tinyusb': {
                            'path': '../tinyusb_local',
                            'version': '*',
                        }
                    },
                    'reason': 'prefer local fork',
                }
            }
        ]
    })

    project_requirements = ProjectRequirements([manifest])

    rule = project_requirements.override_rules['espressif/tinyusb']

    assert rule.name == 'espressif/tinyusb'
    assert rule.origin == 'overrides'
    assert rule.replacement_name == 'my_tinyusb'
    assert rule.source.type == 'local'
    assert rule.source.path == '../tinyusb_local'
    assert rule.version_spec == '*'
    assert rule.reason == 'prefer local fork'
    # A single canonical entry is registered per override. The short form is not a
    # separate key; lookups normalize the requirement name to the canonical form.
    assert list(project_requirements.override_rules) == ['espressif/tinyusb']
    assert 'tinyusb' not in project_requirements.override_rules
    # Messages still use the target as the user wrote it.
    assert rule.reported_name == 'tinyusb'


def test_manifest_canonicalizes_mixed_case_qualified_override_names():
    manifest = Manifest.fromdict({
        'overrides': [
            {
                'Espressif/TinyUSB': {
                    'with': {
                        'My_Namespace/MyTinyUSB': {
                            'path': '../tinyusb_root_override',
                            'version': '*',
                        }
                    }
                }
            }
        ]
    })

    assert manifest.overrides[0].target == 'espressif/tinyusb'
    assert manifest.overrides[0].replacement_name == 'my_namespace/mytinyusb'


def test_manifest_rejects_idf_override():
    errors = Manifest.validate_manifest({
        'overrides': [
            {
                'IDF': {
                    'with': {
                        'idf': {
                            'path': '../idf_override',
                            'version': '*',
                        }
                    }
                }
            }
        ]
    })

    assert errors == ['Invalid field "overrides:idf": ESP-IDF dependency cannot be overridden']


def test_manifest_rejects_unknown_key_in_override_entry():
    errors = Manifest.validate_manifest({
        'overrides': [
            {
                'espressif/tinyusb': {
                    'with': {
                        'my_namespace/mytinyusb': {
                            'path': '../mytinyusb',
                            'version': '*',
                        }
                    },
                    'reasn': 'typo here',
                }
            }
        ]
    })

    assert len(errors) == 1
    assert 'overrides:espressif/tinyusb' in errors[0]
    assert "'reasn'" in errors[0]
    assert 'Unknown key' in errors[0]


def test_manifest_rejects_unknown_key_inside_override_replacement():
    errors = Manifest.validate_manifest({
        'overrides': [
            {
                'espressif/tinyusb': {
                    'with': {
                        'my_namespace/mytinyusb': {
                            'versionn': '*',  # typo: should be "version"
                        }
                    }
                }
            }
        ]
    })

    assert len(errors) == 1
    assert 'Invalid field "overrides:espressif/tinyusb:with:my_namespace/mytinyusb"' in errors[0]
    assert 'versionn' in errors[0]
    assert 'Unknown fields' in errors[0]


@pytest.mark.parametrize('override_path', ['../mytinyusb', None])
def test_manifest_rejects_override_path_in_override_replacement(override_path):
    errors = Manifest.validate_manifest({
        'overrides': [
            {
                'espressif/tinyusb': {
                    'with': {
                        'my_namespace/mytinyusb': {
                            'override_path': override_path,
                            'version': '*',
                        }
                    }
                }
            }
        ]
    })

    assert errors == [
        'Invalid field "overrides:espressif/tinyusb:with:my_namespace/mytinyusb:override_path": '
        '"override_path" is not supported in override replacements. Use "path" instead.'
    ]


def test_manifest_rejects_duplicate_override_keys_after_canonicalization():
    with pytest.raises(ValueError) as excinfo:
        Manifest.fromdict({
            'overrides': [
                {
                    'tinyusb': {
                        'with': {
                            'my_tinyusb': {
                                'path': '../tinyusb_root_override',
                                'version': '*',
                            }
                        }
                    }
                },
                {
                    'Espressif/TinyUSB': {
                        'with': {
                            'another_tinyusb': {
                                'path': '../tinyusb_other_override',
                                'version': '*',
                            }
                        }
                    }
                },
            ]
        })

    assert (
        'Duplicate override target after normalization: "Espressif/TinyUSB" and "tinyusb"'
        in str(excinfo.value)
    )


def test_project_requirements_uses_manifest_normalized_override_keys():
    manifest = Manifest.fromdict({
        'dependencies': {
            'Espressif/TinyUSB': {
                'version': '~1.0',
                'override_path': '../tinyusb_override',
            }
        },
        'overrides': [
            {
                'Espressif/TinyUSB': {
                    'with': {
                        'My_Namespace/MyTinyUSB': {
                            'path': '../tinyusb_root_override',
                            'version': '*',
                        }
                    }
                }
            }
        ],
    })

    project_requirements = ProjectRequirements([manifest])

    assert set(project_requirements.override_rules.keys()) == {'espressif/tinyusb'}
    rule = project_requirements.override_rules['espressif/tinyusb']
    assert rule.name == 'espressif/tinyusb'
    assert rule.origin == 'overrides'
    assert rule.replacement_name == 'my_namespace/mytinyusb'
    assert rule.source.path == '../tinyusb_root_override'


def test_project_requirements_collects_override_path_rules():
    manifest = Manifest.fromdict({
        'dependencies': {
            'tinyusb': {
                'version': '~1.0',
                'override_path': '../tinyusb_override',
            }
        }
    })

    project_requirements = ProjectRequirements([manifest])

    rule = project_requirements.override_rules['espressif/tinyusb']

    assert rule.name == 'espressif/tinyusb'
    assert rule.origin == 'override_path'
    assert rule.source.type == 'local'
    assert rule.source.override_path == '../tinyusb_override'
    assert rule.version_spec == '~1.0'
    assert rule.reason is None


def test_project_requirements_skips_inactive_override_path_rules(monkeypatch):
    monkeypatch.setenv('IDF_TARGET', 'esp32')
    manifest = Manifest.fromdict({
        'dependencies': {
            'tinyusb': {
                'version': '~1.0',
                'override_path': '../tinyusb_override',
                'rules': [{'if': 'target == "esp32s3"'}],
            }
        }
    })

    project_requirements = ProjectRequirements([manifest])

    assert project_requirements.override_rules == {}


def test_project_requirements_skips_inactive_overrides(monkeypatch):
    monkeypatch.setenv('IDF_TARGET', 'esp32')
    manifest = Manifest.fromdict({
        'overrides': [
            {
                'tinyusb': {
                    'with': {
                        'my_tinyusb': {
                            'path': '../tinyusb_root_override',
                            'version': '*',
                            'rules': [{'if': 'target == "esp32s3"'}],
                        }
                    }
                }
            }
        ]
    })

    notices = []
    monkeypatch.setattr('idf_component_tools.utils.notice', notices.append)
    project_requirements = ProjectRequirements([manifest])

    assert project_requirements.override_rules == {}
    assert any('Override for "espressif/tinyusb" is inactive' in notice for notice in notices)


def test_project_requirements_collects_active_conditional_override(monkeypatch):
    monkeypatch.setenv('IDF_TARGET', 'esp32')
    manifest = Manifest.fromdict({
        'overrides': [
            {
                'tinyusb': {
                    'with': {
                        'my_tinyusb': {
                            'path': '../tinyusb_root_override',
                            'version': '*',
                            'rules': [{'if': 'target == "esp32"'}],
                        }
                    }
                }
            }
        ]
    })

    project_requirements = ProjectRequirements([manifest])

    assert set(project_requirements.override_rules.keys()) == {'espressif/tinyusb'}
    assert project_requirements.override_rules['espressif/tinyusb'].origin == 'overrides'


def test_project_requirements_overrides_win_over_override_path():
    manifest = Manifest.fromdict({
        'dependencies': {
            'Espressif/TinyUSB': {
                'version': '~1.0',
                'override_path': '../tinyusb_override',
            }
        },
        'overrides': [
            {
                'Espressif/TinyUSB': {
                    'with': {
                        'My_Namespace/MyTinyUSB': {
                            'path': '../tinyusb_root_override',
                            'version': '~2.0',
                        }
                    },
                    'reason': 'use override instead',
                }
            }
        ],
    })

    project_requirements = ProjectRequirements([manifest])

    rule = project_requirements.override_rules['espressif/tinyusb']

    assert rule.origin == 'overrides'
    assert rule.replacement_name == 'my_namespace/mytinyusb'
    assert rule.source.path == '../tinyusb_root_override'
    assert rule.source.override_path is None
    assert rule.version_spec == '~2.0'
    assert rule.reason == 'use override instead'


def test_project_requirements_collects_overrides_from_any_manifest():
    manifest_without_override = Manifest.fromdict({})
    manifest_with_override = Manifest.fromdict({
        'overrides': [
            {
                'tinyusb': {
                    'with': {
                        'my_tinyusb': {
                            'path': '../tinyusb_child_override',
                            'version': '*',
                        }
                    }
                }
            }
        ]
    })

    project_requirements = ProjectRequirements([manifest_without_override, manifest_with_override])

    rule = project_requirements.override_rules['espressif/tinyusb']
    assert rule.origin == 'overrides'
    assert rule.source.path == '../tinyusb_child_override'


def test_project_requirements_child_overrides_change_manifest_hash():
    manifest = Manifest.fromdict({})
    child_manifest_without_override = Manifest.fromdict({})
    child_manifest_with_override = Manifest.fromdict({
        'overrides': [
            {
                'tinyusb': {
                    'with': {
                        'my_tinyusb': {
                            'path': '../tinyusb_child_override',
                            'version': '*',
                        }
                    }
                }
            }
        ]
    })

    project_requirements_without_override = ProjectRequirements([
        manifest,
        child_manifest_without_override,
    ])
    project_requirements_with_override = ProjectRequirements([
        manifest,
        child_manifest_with_override,
    ])

    assert (
        project_requirements_without_override.manifest_hash
        != project_requirements_with_override.manifest_hash
    )


def test_project_requirements_rejects_overrides_in_multiple_manifests():
    def _override_manifest(replacement_path):
        return Manifest.fromdict({
            'overrides': [
                {
                    'tinyusb': {
                        'with': {
                            'my_tinyusb': {
                                'path': replacement_path,
                                'version': '*',
                            }
                        }
                    }
                }
            ]
        })

    manifest_a = _override_manifest('../tinyusb_a_override')
    manifest_b = _override_manifest('../tinyusb_b_override')

    with pytest.raises(ManifestError) as excinfo:
        ProjectRequirements([manifest_a, manifest_b])

    assert 'Field "overrides" can be defined in only one manifest' in str(excinfo.value)


@pytest.mark.parametrize('empty_overrides', [[], None])
def test_project_requirements_ignores_empty_overrides_in_multiple_manifests(empty_overrides):
    """An empty (or omitted) ``overrides`` field must not count as a declaration,
    so it never conflicts with a real ``overrides`` declared elsewhere."""
    manifest_a = Manifest(overrides=empty_overrides)
    manifest_b = Manifest(overrides=empty_overrides)
    manifest_c = Manifest.fromdict({
        'overrides': [
            {
                'tinyusb': {
                    'with': {
                        'my_tinyusb': {
                            'path': '../tinyusb_child_override',
                            'version': '*',
                        }
                    }
                }
            }
        ]
    })

    # Two empty-overrides manifests do not conflict with each other ...
    assert ProjectRequirements([manifest_a, manifest_b]).override_rules == {}
    # ... nor with a single real override declaration.
    assert ProjectRequirements([manifest_a, manifest_c]).override_rules != {}
