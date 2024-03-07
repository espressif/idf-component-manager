# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0


from typing import Dict, List

import yaml
from schema import Schema, SchemaError

from idf_component_tools.errors import ProcessingError

COMPONENT_LIST_SCHEMA = Schema(
    {
        'components': [
            {'name': str, 'path': str},
        ]
    },
    ignore_extra_keys=True,
)


def parse_component_list(path: str) -> List[Dict[str, str]]:
    with open(path, encoding='utf-8') as f:
        try:
            components = COMPONENT_LIST_SCHEMA.validate(yaml.safe_load(f.read()))
            return components['components']
        except (yaml.YAMLError, SchemaError):
            raise ProcessingError('Cannot parse components list file.')
