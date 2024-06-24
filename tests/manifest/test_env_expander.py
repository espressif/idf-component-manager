# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import pytest

from idf_component_tools.errors import ManifestError, RunningEnvironmentError
from idf_component_tools.manifest.if_parser import parse_if_clause
from idf_component_tools.utils import (
    subst_vars_in_str,
)

TEST_ENVIRON = {
    'A': '',
    'B': 'b',
}


@pytest.mark.parametrize(
    'inp,env,exp',
    [
        ('100', {}, '100'),
        ('${A}100', TEST_ENVIRON, '100'),
        ('$A 100$B', TEST_ENVIRON, ' 100b'),
        ('$$100', {}, '$100'),
    ],
)
def test_expand_env_vars_in_str_ok(inp, env, exp):
    assert subst_vars_in_str(inp, env) == exp


@pytest.mark.parametrize(
    'inp,env',
    [
        ('$A100', TEST_ENVIRON),
        ('$ABC', TEST_ENVIRON),
    ],
)
def test_expand_env_vars_in_str_env_not_set_err(inp, env):
    with pytest.raises(RunningEnvironmentError, match='Environment variable.+is not set'):
        subst_vars_in_str(inp, env)


@pytest.mark.parametrize(
    'inp,env',
    [
        ('$100', TEST_ENVIRON),
        ('${A', TEST_ENVIRON),
    ],
)
def test_expand_env_vars_in_str_env_format_err(inp, env):
    with pytest.raises(
        ManifestError, match='Invalid format of environment variable in the value.+'
    ):
        subst_vars_in_str(inp, env)


@pytest.mark.parametrize(
    'if_clause',
    [
        'target == esp32 && ${FOO} in [ "FOO" ]',
        '${FOO}_BAR == "FOO_BAR"',
        '${VER} < 2.11',
    ],
)
def test_expand_env_vars_with_optional_dependencies(if_clause, monkeypatch):
    monkeypatch.setenv('IDF_TARGET', 'esp32')

    clause = parse_if_clause(if_clause)

    monkeypatch.setenv('FOO', 'FOO')
    monkeypatch.setenv('VER', '2.9.0')
    assert clause.get_value() is True

    monkeypatch.delenv('FOO')
    monkeypatch.delenv('VER')
    with pytest.warns(
        UserWarning, match='Environment variable.+is not set, assume the condition is False'
    ):
        assert clause.get_value() is False
