# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os
import typing as t
from string import Template

import yaml

from idf_component_tools.errors import ManifestError


def subst_vars_in_str(s: str, env: t.Dict[str, t.Any]) -> str:
    try:
        return Template(s).substitute(env)
    except KeyError as e:
        raise ManifestError(f'Environment variable "{e.args[0]}" is not set')
    except ValueError:
        raise ManifestError(
            'Invalid format of environment variable in the value: "{}".\n'
            'Note: you can use "$$" to escape the "$" character'.format(s)
        )


def expand_env_vars(
    obj: t.Union[t.Dict[str, t.Any], t.List, str, t.Any],
    env: t.Optional[t.Dict] = None,
) -> t.Union[t.Dict[str, t.Any], t.List, str, t.Any]:
    """
    Expand variables in the results of YAML/JSON file parsing
    """
    if env is None:
        env = dict(os.environ)

    def expand_env_in_str(value):
        return subst_vars_in_str(value, env)

    # we don't process other data types, like numbers
    return process_nested_strings(obj, expand_env_in_str)


class EnvFoundException(Exception):
    pass


def _raise_on_env(s: str) -> None:
    try:
        Template(s).substitute({})
    except (KeyError, ValueError):
        raise EnvFoundException


def contains_env_variables(obj: t.Union[t.Dict[str, t.Any], t.List, str, t.Any]) -> bool:
    try:
        process_nested_strings(obj, _raise_on_env)
        return False
    except EnvFoundException:
        return True


def process_nested_strings(
    obj: t.Union[t.Dict[str, t.Any], t.List, str, t.Any],
    func: t.Callable[[str], t.Any],
) -> t.Union[t.Dict[str, t.Any], t.List, str, t.Any]:
    """
    Recursively process strings in the results of YAML/JSON file parsing
    """

    if isinstance(obj, dict):
        return {k: process_nested_strings(v, func) for k, v in obj.items()}
    elif isinstance(obj, str):
        return func(obj)
    elif isinstance(obj, (list, tuple)):
        # yaml dict won't have other iterable data types
        return [process_nested_strings(i, func) for i in obj]

    # we don't process other data types, like numbers
    return obj


def dump_escaped_yaml(d: t.Dict[str, t.Any], path: str) -> None:
    def _escape_dollar_sign(s):
        return s.replace('$', '$$')

    with open(path, 'w', encoding='utf-8') as fw:
        yaml.dump(
            process_nested_strings(d, _escape_dollar_sign),
            fw,
            allow_unicode=True,
            Dumper=yaml.SafeDumper,
        )
