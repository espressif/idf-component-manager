# SPDX-FileCopyrightText: 2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import typing as t

import jsonref
from pydantic_core import core_schema

from idf_component_tools.errors import MetadataError

from .constants import KNOWN_BUILD_METADATA_FIELDS, KNOWN_INFO_METADATA_FIELDS
from .models import Manifest

# `if` is aliased
MANIFEST_JSON_SCHEMA = Manifest.model_json_schema(by_alias=True)
# we have one rename in the manifest model
# dependencies-*-service_url-type:string -> dependencies-*-registry_url-type:string
# manually add it in the json schema
MANIFEST_JSON_SCHEMA['$defs']['DependencyItem']['properties']['service_url'] = MANIFEST_JSON_SCHEMA[
    '$defs'
]['DependencyItem']['properties']['registry_url']


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
    elif 'const' in schema:
        return [stack + ['type:' + type(schema['const']).__name__.replace('bool', 'boolean')]]
    elif schema['type'] == 'object':
        res = []
        if 'properties' in schema and schema['properties']:
            for k, v in schema['properties'].items():
                # v is a dictionary
                cur = stack + [k]

                if 'type' not in v:
                    res.extend(_flatten_json_schema_keys(v, cur))
                elif v['type'] == 'object':
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


def flatten_manifest_file_keys(manifest_tree, stack=None, level=1):
    if stack is None:
        stack = []

    res = []
    if isinstance(manifest_tree, dict):
        for k, v in manifest_tree.items():
            cur = stack + [k]

            if k == 'dependencies' and level == 1:
                if isinstance(v, dict):
                    for _k, _v in v.items():
                        # _k doesn't matter here, use '*'
                        res.extend(flatten_manifest_file_keys(_v, cur + ['*'], level + 1))
                else:
                    # List of components should be a dictionary.
                    raise MetadataError(
                        'List of dependencies should be a dictionary.'
                        ' For example:\ndependencies:\n  some-component: ">=1.2.3,!=1.2.5"'
                    )
            else:
                res.extend(flatten_manifest_file_keys(v, cur, level + 1))

    elif isinstance(manifest_tree, (list, set)):
        for item in manifest_tree:
            res.extend(flatten_manifest_file_keys(item, stack + ['type:array'], level + 1))
    else:
        if isinstance(manifest_tree, bool):
            res.append(stack + ['type:boolean'])
        elif isinstance(manifest_tree, str):
            res.append(stack + ['type:string'])
        elif isinstance(manifest_tree, (int, float)):
            res.append(stack + ['type:number'])
        elif isinstance(manifest_tree, type(None)):
            pass
        else:
            raise MetadataError(
                'Unknown key type {} for key {}'.format(type(manifest_tree), manifest_tree)
            )

    return res


_build_metadata_keys: t.List[str] = []
_info_metadata_keys: t.List[str] = []
# jsonref to resolve all the references
# TODO: maybe turn it into a file packaged with the library
_schema_without_ref = jsonref.replace_refs(MANIFEST_JSON_SCHEMA, jsonschema=True)
_flattened_json_schema_keys = _flatten_json_schema_keys(_schema_without_ref)


for _key in sorted(_flattened_json_schema_keys):
    if _key[0] in KNOWN_BUILD_METADATA_FIELDS:
        _build_metadata_keys.append(_key)
    elif _key[0] in KNOWN_INFO_METADATA_FIELDS:
        _info_metadata_keys.append(_key)
    else:
        raise ValueError('Unknown JSON Schema key {}'.format(_key[0])).with_traceback(None)

BUILD_METADATA_KEYS = serialize_list_of_list_of_strings(_build_metadata_keys)
INFO_METADATA_KEYS = serialize_list_of_list_of_strings(_info_metadata_keys)

METADATA_JSON_SCHEMA = core_schema.typed_dict_schema({
    'build_keys': core_schema.typed_dict_field(core_schema.literal_schema(BUILD_METADATA_KEYS)),
    'info_keys': core_schema.typed_dict_field(core_schema.literal_schema(INFO_METADATA_KEYS)),
})
