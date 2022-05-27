import os
from string import Template

from ..errors import ManifestError

try:
    from typing import Any
except ImportError:
    pass


def _expand_env_vars_in_str(s, env):  # type: (str, dict[str, Any]) -> str
    try:
        return Template(s).substitute(env)
    except KeyError as e:
        raise ManifestError(
            'Using environment variable "{}" in the manifest file but not specifying it'.format(e.args[0]))


def expand_env_vars(
        obj,  # type: dict[str, Any] | list | str | Any
        env=None  # type: dict | None
):
    # type: (...) -> dict[str, Any] | list | str | Any
    '''
    Expand variables in the results of YAML/JSON file parsing
    '''
    if env is None:
        env = dict(os.environ)

    if isinstance(obj, dict):
        return {k: expand_env_vars(v, env) for k, v in obj.items()}
    elif isinstance(obj, str):
        return _expand_env_vars_in_str(obj, env)
    elif isinstance(obj, list):
        # yaml dict won't have other iterable data types like set or tuple
        return [expand_env_vars(i, env) for i in obj]

    # we don't process other data types, like numbers
    return obj
