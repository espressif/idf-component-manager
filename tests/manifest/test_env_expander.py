# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import pytest

from idf_component_tools.errors import ManifestError
from idf_component_tools.manifest.env_expander import (
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
    'inp,env,err',
    [
        ('$100', TEST_ENVIRON, 'Invalid'),
        ('$A100', TEST_ENVIRON, 'not set'),
    ],
)
def test_expand_env_vars_in_str_err(inp, env, err):
    with pytest.raises(ManifestError, match=err):
        subst_vars_in_str(inp, env)
