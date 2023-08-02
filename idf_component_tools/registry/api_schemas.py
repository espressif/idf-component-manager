# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

from schema import Optional, Or, Schema, Use
from six import string_types

STRING = Or(*string_types)
OPTIONAL_STRING = Or(None, *string_types)

ERROR_SCHEMA = Schema(
    {
        'error': STRING,
        'messages': Or([STRING], {STRING: object}),
        Optional(STRING): object,
    },
    error='Unexpected error format',
)

OPTIONAL_DEPENDENCY = {'if': STRING, Optional('version'): STRING}

DEPENDENCY = {
    'spec': STRING,
    'source': STRING,
    Optional('name'): OPTIONAL_STRING,
    Optional('namespace'): OPTIONAL_STRING,
    Optional('is_public'): Use(bool),
    Optional('require'): Use(bool),
    Optional('rules'): [OPTIONAL_DEPENDENCY],
    Optional('matches'): [OPTIONAL_DEPENDENCY],
    Optional(Use(str)): object,
}

VERSION = {
    'version': STRING,
    'component_hash': STRING,
    'url': STRING,
    Optional('dependencies'): [DEPENDENCY],
    Optional('targets'): Or([STRING], None),
    Optional(STRING): object,
}

COMPONENT_SCHEMA = Schema(
    {
        'name': STRING,
        'namespace': STRING,
        'versions': [VERSION],
        Optional(STRING): object,
    },
    error='Unexpected format of the component',
)

VERSION_UPLOAD_SCHEMA = Schema(
    {
        'job_id': STRING,
        Optional(STRING): object,
    },
    error='Unexpected response during archive processing',
)

TASK_STATUS_SCHEMA = Schema(
    {
        'id': STRING,
        'status': STRING,
        Optional('message'): OPTIONAL_STRING,
        Optional('progress'): Or(Use(float), None),
        Optional(STRING): object,
    }
)

API_INFORMATION_SCHEMA = Schema(
    {'components_base_url': STRING, 'info': STRING, 'status': STRING, 'version': STRING},
    error='Unexpected response to API information',
)

API_TOKEN_SCHEMA = Schema(
    {
        'id': STRING,
        'scope': STRING,
        'created_at': OPTIONAL_STRING,
        'expires_at': OPTIONAL_STRING,
        'description': OPTIONAL_STRING,
        'access_token_prefix': STRING,
    },
    error='Unexpected response to current token information',
)
