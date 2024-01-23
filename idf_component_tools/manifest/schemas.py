# SPDX-FileCopyrightText: 2023-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import re

from schema import And, Optional, Or, Regex, Schema, Use
from six import reraise, string_types

from idf_component_manager.utils import RE_PATTERN

from ..constants import COMPILED_GIT_URL_RE, COMPILED_URL_RE
from ..errors import InternalError
from ..semver import SimpleSpec, Version
from .constants import (
    COMMIT_ID_RE,
    FULL_SLUG_REGEX,
    KNOWN_BUILD_METADATA_FIELDS,
    KNOWN_INFO_METADATA_FIELDS,
    TAGS_REGEX,
)
from .if_parser import IfClause, OptionalDependency, parse_if_clause

try:
    import typing as t
except ImportError:
    pass

KNOWN_FILES_KEYS = [
    'include',
    'exclude',
]
KNOWN_EXAMPLES_KEYS = ['path']
KNOWN_IF_CLAUSE_KEYWORDS = ['IDF_TARGET', 'IDF_VERSION']

LINKS_URL_ERROR = 'Invalid URL in the "{}" field. Check that link is a correct HTTP(S) URL. '
LINKS_GIT_ERROR = 'Invalid URL in the "{}" field. Check that link is a valid Git remote URL'


def _nonempty_string(field):  # type: (str) -> And
    return And(
        Or(*string_types), len, error='Non-empty string is required in the "{}" field'.format(field)
    )


def expanded_optional_dependency_schema_builder():  # type: () -> Schema
    return And(
        {
            'if': Use(parse_if_clause),
            Optional('version'): Or(
                None, *string_types, error='Dependency version spec format in rule/match is invalid'
            ),
        },
        Use(OptionalDependency.fromdict),
    )


def optional_dependency_schema_builder():  # type: () -> Schema
    return {
        'if': Or(*string_types),
        Optional('version'): Or(
            None, *string_types, error='Dependency version spec format in rule/match is invalid'
        ),
    }


def dependency_schema_builder(rule_schema_builder):  # type: (t.Callable) -> Or
    return Or(
        Or(None, *string_types, error='Dependency version spec format is invalid'),
        {
            Optional('version'): Or(
                None, *string_types, error='Dependency version spec format is invalid'
            ),
            Optional('public'): Use(
                bool,
                error='Invalid format of dependency public flag',
            ),
            Optional('path'): _nonempty_string('path'),
            Optional('git'): _nonempty_string('git'),
            Optional('service_url'): _nonempty_string('service_url'),
            Optional('rules'): [rule_schema_builder()],
            Optional('matches'): [rule_schema_builder()],
            Optional('override_path'): _nonempty_string('override_path'),
            Optional('require'): Or(
                'public',
                'private',
                'no',
                False,
                error='Invalid format of dependency require field format. '
                'Should be "public", "private" or "no"',
            ),
            Optional('pre_release'): Use(
                bool, error='Invalid format of dependency pre_release flag'
            ),
        },
        error='Invalid dependency format',
    )


def repository_info_schema_builder():
    return Schema(
        {
            Optional('commit_sha'): Regex(COMMIT_ID_RE, error='Invalid git commit SHA format'),
            Optional('path'): _nonempty_string('repository_path'),
        }
    )


def schema_builder(validate_rules=False):  # type: (bool) -> Schema
    if validate_rules:
        rule_builder = expanded_optional_dependency_schema_builder
    else:
        rule_builder = optional_dependency_schema_builder

    dependency_schema = dependency_schema_builder(rule_builder)
    repository_info_schema = repository_info_schema_builder()

    return Schema(
        {
            Optional('name'): Or(*string_types),
            Optional('version'): Or(
                Version.parse, error='Component version should be valid semantic version'
            ),
            Optional('targets'): [_nonempty_string('targets')],
            Optional('maintainers'): [_nonempty_string('maintainers')],
            Optional('description'): _nonempty_string('description'),
            Optional('license'): _nonempty_string('license'),
            Optional('tags'): [
                Regex(
                    TAGS_REGEX,
                    error='Invalid tag. Tags may be between 3 and 32 symbols long and may contain '
                    'letters, numbers, _ and -',
                )
            ],
            Optional('dependencies'): {
                Optional(
                    Regex(FULL_SLUG_REGEX, error='Invalid name for dependency')
                ): dependency_schema
            },
            Optional('files'): {
                Optional(key): [_nonempty_string('files')] for key in KNOWN_FILES_KEYS
            },
            Optional('examples'): [
                {key: _nonempty_string('examples') for key in KNOWN_EXAMPLES_KEYS}
            ],
            # Links of the project
            Optional('url'): Regex(COMPILED_URL_RE, error=LINKS_URL_ERROR.format('url')),
            Optional('repository'): Regex(
                COMPILED_GIT_URL_RE, error=LINKS_GIT_ERROR.format('repository')
            ),
            Optional('documentation'): Regex(
                COMPILED_URL_RE, error=LINKS_URL_ERROR.format('documentation')
            ),
            Optional('issues'): Regex(COMPILED_URL_RE, error=LINKS_URL_ERROR.format('issues')),
            Optional('discussion'): Regex(
                COMPILED_URL_RE, error=LINKS_URL_ERROR.format('discussion')
            ),
            Optional('repository_info'): repository_info_schema,
            # allow any other fields
            Optional(str): object,
        },
        error='Invalid manifest format',
    )


def version_json_schema():  # type: () -> dict
    return {'type': 'string', 'pattern': SimpleSpec.regex_str()}


def manifest_json_schema():  # type: () -> dict
    def replace_regex_pattern_with_pattern_str(pat):  # type: (re.Pattern) -> t.Any
        return pat.pattern

    def process_json_schema(
        obj,  # type: dict[str, t.Any] | list | str | t.Any
    ):  # type: (...) -> dict[str, t.Any] | list | str | t.Any
        if isinstance(obj, dict):
            # jsonschema 2.5.1 for python 3.4 does not support empty `required` field
            if not obj.get('required', []):
                obj.pop('required', None)

            return {k: process_json_schema(v) for k, v in obj.items()}
        elif isinstance(obj, RE_PATTERN):
            # `re.Pattern` should use the pattern string instead
            return replace_regex_pattern_with_pattern_str(obj)
        elif isinstance(obj, (list, tuple)):
            # yaml dict won't have other iterable data types
            return [process_json_schema(i) for i in obj]

        # we don't process other data types, like numbers
        return obj

    json_schema = schema_builder().json_schema(
        'idf-component-manager'
    )  # here id should be an url to use $ref in the future

    # Polish starts here

    # The "schema" library we're currently using does not support
    # auto-generate JSON Schema for nested schema.
    # We need to add it back by ourselves
    #
    # `version`
    json_schema['properties']['version'] = version_json_schema()
    # `dependency`
    json_schema['properties']['dependencies']['additionalProperties'] = {
        'anyOf': Schema(dependency_schema_builder(optional_dependency_schema_builder)).json_schema(
            '#dependency'
        )['anyOf']
    }
    # `dependencies:*:version` could be simple spec version,
    # or git branch/commit, use string instead
    _anyof = json_schema['properties']['dependencies']['additionalProperties']['anyOf']
    _anyof[0] = {'type': 'string'}
    _anyof[1]['properties']['version'] = {'type': 'string'}
    # `if` clause
    _anyof[1]['properties']['rules']['items']['properties']['if'] = {
        'type': 'string',
        'pattern': IfClause.regex_str(),
    }
    _anyof[1]['properties']['rules']['items']['properties']['version'] = version_json_schema()
    _anyof[1]['properties']['matches']['items']['properties']['if'] = {
        'type': 'string',
        'pattern': IfClause.regex_str(),
    }
    _anyof[1]['properties']['matches']['items']['properties']['version'] = version_json_schema()

    # The "schema" library is also missing the `type` for the following types
    # - enum - it's optional in JSON schema, but it's important to the error messages
    # - boolean - it's mandatory, otherwise the schema could also accept random strings
    json_schema['properties']['targets']['items']['type'] = 'string'
    _anyof[1]['properties']['pre_release']['type'] = 'boolean'
    _anyof[1]['properties']['public']['type'] = 'boolean'
    _anyof[1]['properties']['require']['type'] = 'string'

    # normalize the final json schema
    json_schema = process_json_schema(json_schema)

    return json_schema


JSON_SCHEMA = manifest_json_schema()


def _flatten_json_schema_keys(schema, stack=None):
    def subschema_key(_schema):
        for sub_k in _schema:
            if sub_k in ['allOf', 'anyOf', 'oneOf', 'not']:
                return sub_k

        return None

    if stack is None:
        stack = []

    subkey = subschema_key(schema)
    if subkey:
        res = []
        for s in schema[subkey]:
            res += _flatten_json_schema_keys(s, stack)
        return res
    elif schema['type'] == 'object':
        res = []
        if 'properties' in schema and schema['properties']:
            for k, v in schema['properties'].items():
                # v is a dictionary
                cur = stack + [k]

                if v['type'] == 'object':
                    res.extend(_flatten_json_schema_keys(v, cur))
                elif v['type'] == 'array':
                    res.extend(_flatten_json_schema_keys(v['items'], cur + ['type:array']))
                else:
                    res.append(cur + ['type:' + v['type']])

        if 'additionalProperties' in schema and schema['additionalProperties']:
            if schema['additionalProperties'] is True:  # arbitrary key value "str: object"
                pass
            else:
                res.extend(_flatten_json_schema_keys(schema['additionalProperties'], stack + ['*']))

        return res
    else:
        return [stack + ['type:' + schema['type']]]


def serialize_list_of_list_of_strings(ll_str):
    """
    flatten list of strings to '-' joined values.

    This would make database storage much easier.
    """
    res = []
    for key in ll_str:
        new_str = '-'.join(key)
        if new_str not in res:
            res.append(new_str)

    return sorted(res)


_build_metadata_keys = []  # type: list[str]
_info_metadata_keys = []  # type: list[str]
for _key in sorted(_flatten_json_schema_keys(JSON_SCHEMA)):
    if _key[0] in KNOWN_BUILD_METADATA_FIELDS:
        _build_metadata_keys.append(_key)
    elif _key[0] in KNOWN_INFO_METADATA_FIELDS:
        _info_metadata_keys.append(_key)
    else:
        reraise(InternalError, ValueError('Unknown JSON Schema key {}'.format(_key[0])))

BUILD_METADATA_KEYS = serialize_list_of_list_of_strings(_build_metadata_keys)
INFO_METADATA_KEYS = serialize_list_of_list_of_strings(_info_metadata_keys)

METADATA_SCHEMA = Schema(
    {
        Optional('build_keys'): BUILD_METADATA_KEYS,
        Optional('info_keys'): INFO_METADATA_KEYS,
    }
)
