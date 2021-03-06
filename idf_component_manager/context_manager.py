# SPDX-FileCopyrightText: 2022 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import threading
from contextlib import contextmanager

local = threading.local()
local.ctx = {}


def get_ctx(name):
    return local.ctx.get(name)


@contextmanager
def make_ctx(name, **kwargs):
    try:
        local.ctx[name] = kwargs
        yield
    finally:
        local.ctx[name] = None
