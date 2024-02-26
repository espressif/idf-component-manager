# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import sys
import warnings

from idf_component_tools.messages import UserDeprecationWarning


def add_options(options):
    def wrapper(func):
        for _option in reversed(options):
            func = _option(func)

        return func

    return wrapper


def deprecated_option(ctx, param, value):
    if any(True for arg in sys.argv if arg.startswith(param.opts[0])):
        warnings.warn(f'The option {param.name} is deprecated.', UserDeprecationWarning)
