# SPDX-FileCopyrightText: 2023-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
from pytest import mark

from idf_component_tools.environment import (
    KNOWN_CI_ENVIRONMENTS,
    ComponentManagerSettings,
    _env_to_bool,
    _env_to_bool_or_string,
    detect_ci,
)


@mark.parametrize(
    ('value', 'expected'),
    [
        ('1', True),
        ('0', False),
        ('true', True),
        ('false', False),
        ('True', True),
        ('False', False),
        ('yes', True),
        ('no', False),
        ('y', True),
        ('n', False),
        ('Y', True),
        ('N', False),
        ('', False),
        ('asdf', False),
    ],
)
def test_env_to_bool(value, expected):
    assert _env_to_bool(value) == expected


def test_detect_ci(monkeypatch):
    # Clear environment variables for github actions and gitlab ci
    for k in KNOWN_CI_ENVIRONMENTS:
        monkeypatch.delenv(k, raising=False)

    # Test when not running in a CI environment
    assert detect_ci() is None

    # Test when running in a known CI environment
    monkeypatch.setenv('APPVEYOR', '1')
    assert detect_ci() == 'appveyor'
    monkeypatch.delenv('APPVEYOR')

    # Test when running in an unknown CI environment
    monkeypatch.setenv('CI', '1')
    assert detect_ci() == 'unknown'


@mark.parametrize(
    ('value', 'expected'),
    [
        ('True', True),
        ('False', False),
        ('yes', True),
        ('no', False),
        ('1', True),
        ('0', False),
        ('t', True),
        ('f', False),
        ('y', True),
        ('n', False),
        ('true', True),
        ('false', False),
        ('yes', True),
        ('no', False),
        ('other', 'other'),
    ],
)
def test_env_to_bool_or_string(value, expected):
    assert _env_to_bool_or_string(value) == expected


class TestComponentManagerSettings:
    def test_get_constraint_files_none(self):
        assert ComponentManagerSettings().constraints == {}

    def test_get_constraint_files_empty_string(self, monkeypatch):
        monkeypatch.setenv('IDF_COMPONENT_CONSTRAINT_FILES', '')
        assert ComponentManagerSettings().constraints == {}

    def test_get_constraint_files_non_existing(self, monkeypatch):
        monkeypatch.setenv(
            'IDF_COMPONENT_CONSTRAINT_FILES', '/path/to/file1.txt;;    /path/to/file2.txt'
        )
        assert ComponentManagerSettings().constraints == {}

    def test_constraints_property_files_only(self, monkeypatch, tmp_path):
        (tmp_path / 'constraints.txt').write_text('esp_timer>=1.0.0\nwifi_provisioning==2.0.0')

        monkeypatch.setenv('IDF_COMPONENT_CONSTRAINT_FILES', str(tmp_path / 'constraints.txt'))

        constraints = ComponentManagerSettings().constraints
        assert len(constraints) == 2
        assert 'espressif/esp_timer' in constraints
        assert 'espressif/wifi_provisioning' in constraints

    def test_constraints_property_string_only(self, monkeypatch):
        monkeypatch.setenv(
            'IDF_COMPONENT_CONSTRAINTS', 'esp_timer>=1.0.0; wifi_provisioning==2.0.0'
        )

        constraints = ComponentManagerSettings().constraints
        assert len(constraints) == 2
        assert 'espressif/esp_timer' in constraints
        assert 'espressif/wifi_provisioning' in constraints

    def test_constraints_property_string_overrides_files(self, monkeypatch, tmp_path):
        (tmp_path / 'constraints.txt').write_text('esp_timer>=1.0.0\nwifi_provisioning==1.0.0')

        monkeypatch.setenv('IDF_COMPONENT_CONSTRAINT_FILES', str(tmp_path / 'constraints.txt'))
        monkeypatch.setenv('IDF_COMPONENT_CONSTRAINTS', 'wifi_provisioning==2.0.0')

        constraints = ComponentManagerSettings().constraints
        assert len(constraints) == 2
        assert 'espressif/esp_timer' in constraints
        assert 'espressif/wifi_provisioning' in constraints
        # String constraint should override file constraint
        from idf_component_manager.version_solver.mixology.range import Range

        assert constraints['espressif/wifi_provisioning'] == Range('2.0.0', '2.0.0', True, True)
