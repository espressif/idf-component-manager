# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os
import typing as t
from string import Template

from idf_component_tools.errors import ManifestError, RunningEnvironmentError


def subst_vars_in_str(s: str, env: t.Dict[str, t.Any] = None) -> str:  # type: ignore
    if env is None:
        env = os.environ

    try:
        return Template(s).substitute(env)
    except KeyError as e:
        raise RunningEnvironmentError(f'Environment variable "{e.args[0]}" is not set')
    except ValueError:
        raise ManifestError(
            'Invalid format of environment variable in the value: "{}".\n'
            'Note: you can use "$$" to escape the "$" character'.format(s)
        )
