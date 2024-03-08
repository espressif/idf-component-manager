# SPDX-FileCopyrightText: 2023-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import typing as t

WEB_SERVICE_REQUIRED_KEYS: t.Dict[str, str] = {}
WEB_SERVICE_OPTIONAL_KEYS = {'pre_release': 'bool', 'storage_url': 'str', 'service_url': 'str'}
