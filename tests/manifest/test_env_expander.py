# SPDX-FileCopyrightText: 2022 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import pytest

from idf_component_tools.errors import ManifestError
from idf_component_tools.manifest.env_expander import expand_env_vars, process_nested_strings, subst_vars_in_str

TEST_ENVIRON = {
    'A': '',
    'B': 'b',
}


@pytest.mark.parametrize(
    'inp,env,exp', [
        ('100', {}, '100'),
        ('${A}100', TEST_ENVIRON, '100'),
        ('$A 100$B', TEST_ENVIRON, ' 100b'),
        ('$$100', {}, '$100'),
    ])
def test_expand_env_vars_in_str_ok(inp, env, exp):
    assert subst_vars_in_str(inp, env) == exp


@pytest.mark.parametrize('inp,env,err', [
    ('$100', TEST_ENVIRON, 'Invalid'),
    ('$A100', TEST_ENVIRON, 'not set'),
])
def test_expand_env_vars_in_str_err(inp, env, err):
    with pytest.raises(ManifestError, match=err):
        subst_vars_in_str(inp, env)


@pytest.mark.parametrize(
    'inp,env,exp', [
        (
            {
                'a': 1,
                'b': None,
                'c': '$A${B}C'
            },
            TEST_ENVIRON,
            {
                'a': 1,
                'b': None,
                'c': 'bC'
            },
        ), (
            {
                'a': ['1', '2', '3'],
            },
            {},
            {
                'a': ['1', '2', '3'],
            },
        ), (
            {
                'a': [{
                    'b': '$B'
                }],
            },
            TEST_ENVIRON,
            {
                'a': [{
                    'b': 'b'
                }],
            },
        )
    ])
def test_env_expander(inp, env, exp):
    assert expand_env_vars(inp, env) == exp


@pytest.mark.parametrize(
    'inp,exp_order,exp', [
        (
            {
                'a': 1,
                'b': None,
                'c': 'C',
                'd': {
                    1: 1
                }
            },
            ['C'],
            {
                'a': 1,
                'b': None,
                'c': 1,
                'd': {
                    1: 1
                }
            },
        ),
        (
            {
                'a': ['0', '1', '2', '3']
            },
            ['0', '1', '2', '3'],
            {
                'a': [1, 2, 3, 4]
            },
        ),
        (
            [1, 2, 'b', (3, 'd')],
            ['b', 'd'],
            [1, 2, 1, [3, 2]],
        ),
    ])
def test_process_nested_strings(inp, exp_order, exp):
    order = []

    def acc(v):
        order.append(v)
        return len(order)

    assert exp == process_nested_strings(inp, acc)
    assert order == exp_order
