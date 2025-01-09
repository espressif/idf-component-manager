# SPDX-FileCopyrightText: 2024-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os
from functools import wraps

import vcr


def use_vcr_or_real_env(*args, **kwargs):
    def decorator(func):
        @wraps(func)
        def wrapper(*f_args, **f_kwargs):
            if 'USE_REGISTRY' in os.environ:
                return func(*f_args, **f_kwargs)
            else:
                with vcr.use_cassette(*args, **kwargs):
                    return func(*f_args, **f_kwargs)

        return wrapper

    return decorator
