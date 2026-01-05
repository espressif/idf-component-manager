# SPDX-FileCopyrightText: 2022-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0


import jsonschema

from idf_component_tools.manifest import MANIFEST_JSON_SCHEMA


def test_json_schema():
    validator = jsonschema.Draft7Validator
    validator.check_schema(MANIFEST_JSON_SCHEMA)
