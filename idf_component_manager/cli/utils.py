# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
def add_options(options):
    def wrapper(func):
        for _option in reversed(options):
            func = _option(func)

        return func

    return wrapper
