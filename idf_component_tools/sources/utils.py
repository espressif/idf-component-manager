# SPDX-FileCopyrightText: 2022 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

from idf_component_tools.constants import DEFAULT_NAMESPACE


def normalized_name(name):
    if '/' not in name:
        name = '/'.join([DEFAULT_NAMESPACE, name])

    return name
