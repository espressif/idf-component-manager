# SPDX-FileCopyrightText: 2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
# Make lru_cache available in older pythons
try:
    from functools32 import lru_cache
except ImportError:
    from functools import lru_cache
