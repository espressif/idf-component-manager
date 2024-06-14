# SPDX-FileCopyrightText: 2023-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
from pytest import mark

from idf_component_tools.environment import (
    KNOWN_CI_ENVIRONMENTS,
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
