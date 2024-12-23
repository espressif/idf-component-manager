# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import json

import jsonschema

from idf_component_tools.manifest import MANIFEST_JSON_SCHEMA


def test_json_schema():
    schema_str = json.dumps(MANIFEST_JSON_SCHEMA)

    try:
        validator = jsonschema.Draft7Validator
    except AttributeError:
        validator = jsonschema.Draft4Validator  # python 3.4

    validator.check_schema(json.loads(schema_str))
