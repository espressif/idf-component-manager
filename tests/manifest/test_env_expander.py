import pytest

from idf_component_tools.manifest.env_expander import expand_env_vars

TEST_ENVIRON = {
    'A': '',
    'B': 'b',
}


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
