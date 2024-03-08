# SPDX-FileCopyrightText: 2023-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import typing as t

from ..errors import MetadataError
from .constants import KNOWN_BUILD_METADATA_FIELDS, KNOWN_INFO_METADATA_FIELDS
from .schemas import serialize_list_of_list_of_strings


def _flatten_manifest_file_keys(manifest_tree, stack=None, level=1):
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
                        res.extend(_flatten_manifest_file_keys(_v, cur + ['*'], level + 1))
                else:
                    # List of components should be a dictionary.
                    raise MetadataError(
                        'List of dependencies should be a dictionary.'
                        ' For example:\ndependencies:\n  some-component: ">=1.2.3,!=1.2.5"'
                    )
            else:
                res.extend(_flatten_manifest_file_keys(v, cur, level + 1))

    elif isinstance(manifest_tree, (list, set)):
        for item in manifest_tree:
            res.extend(_flatten_manifest_file_keys(item, stack + ['type:array'], level + 1))
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
            raise MetadataError(f'Unknown key type {type(manifest_tree)} for key {manifest_tree}')

    return res


class Metadata:
    def __init__(self, build_metadata_keys=None, info_metadata_keys=None):
        self.build_metadata_keys = build_metadata_keys or []
        self.info_metadata_keys = info_metadata_keys or []

    @classmethod
    def load(cls, manifest_tree: t.Dict) -> 'Metadata':
        build_metadata_keys, info_metadata_keys = cls._parse_metadata_from_manifest(manifest_tree)

        return cls(build_metadata_keys, info_metadata_keys)

    @classmethod
    def _parse_metadata_from_manifest(
        cls, manifest_tree: t.Any
    ) -> t.Tuple[t.List[str], t.List[str]]:
        metadata_keys = _flatten_manifest_file_keys(manifest_tree)
        build_metadata_keys = []
        info_metadata_keys = []

        for _k in metadata_keys:
            if _k[0] in KNOWN_BUILD_METADATA_FIELDS:
                if _k not in build_metadata_keys:
                    build_metadata_keys.append(_k)
            elif _k[0] in KNOWN_INFO_METADATA_FIELDS:
                if _k not in info_metadata_keys:
                    info_metadata_keys.append(_k)
            # unknown root key, ignore it

        return serialize_list_of_list_of_strings(
            build_metadata_keys
        ), serialize_list_of_list_of_strings(info_metadata_keys)

    @staticmethod
    def get_closest_manifest_key_and_type(
        metadata_key: t.Union[str, t.List[str]],
    ) -> t.Tuple[str, str]:
        """
        One metadata key should look like "dependencies-*-rules-type:array-if-type:string",
        or ['dependencies', '*', 'rules', 'type:array', 'if', 'type:string'] if it's a list

        `type:...` is the type of this field

        The output of the above example should be `if`, `string`,
        """
        if isinstance(metadata_key, list):
            parts = metadata_key
        else:
            parts = metadata_key.split('-')

        types = []
        key = None
        for i, part in enumerate(parts[::-1]):
            if 'type:' in part:
                types.append(part)
            elif part == '*':  # any str could be the key
                key = f'{parts[i - 1]}:*'
                break
            else:
                key = part
                break

        if not key:
            raise ValueError(
                f'manifest key is not found in metadata key: "{metadata_key}"'
            ).with_traceback(None)

        return key, ' of '.join([_t.split('type:')[-1] for _t in types[::-1]])
