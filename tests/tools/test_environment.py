# SPDX-FileCopyrightText: 2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
from pytest import mark, raises

from idf_component_tools.environment import getenv_bool, getenv_int


@mark.parametrize(
    ('value', 'expected'), [
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
    ])
def test_getenv_bool(value, expected, monkeypatch):
    monkeypatch.setenv('TEST_GETENV_BOOL', value)
    assert getenv_bool('TEST_GETENV_BOOL') == expected


def test_getenv_bool_true(monkeypatch):
    monkeypatch.setenv('TEST_GETENV_BOOL_TRUE', '0')
    assert not getenv_bool('TEST_GETENV_BOOL_TRUE', True)

    monkeypatch.delenv('TEST_GETENV_BOOL_TRUE')
    assert getenv_bool('TEST_GETENV_BOOL_TRUE', True)


def test_getenv_int_ok(monkeypatch):
    monkeypatch.setenv('TEST_GETENV_INT_OK', '1000')
    assert getenv_int('TEST_GETENV_INT_OK', 5) == 1000


def test_getenv_int_err(monkeypatch):
    monkeypatch.setenv('TEST_GETENV_INT_ERR', '1aaa')

    with raises(ValueError, match='Environment variable "TEST_GETENV_INT_ERR" must contain a numeric value'):
        getenv_int('TEST_GETENV_INT_ERR', 5)


def test_getenv_int_unset(monkeypatch):
    monkeypatch.delenv('TEST_GETENV_INT_UNSET', raising=False)
    assert getenv_int('TEST_GETENV_INT_UNSET', 5) == 5
