# SPDX-FileCopyrightText: 2023-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import typing as t

from .constants import KNOWN_BUILD_METADATA_FIELDS, KNOWN_INFO_METADATA_FIELDS
from .schemas import flatten_manifest_file_keys, serialize_list_of_list_of_strings


class Metadata(object):
    def __init__(self, build_metadata_keys=None, info_metadata_keys=None):
        self.build_metadata_keys = build_metadata_keys or []
        self.info_metadata_keys = info_metadata_keys or []

    @classmethod
    def load(cls, manifest_tree: t.Dict) -> 'Metadata':
        build_metadata_keys, info_metadata_keys = cls.parse_metadata_from_manifest(manifest_tree)

        return cls(build_metadata_keys, info_metadata_keys)

    @classmethod
    def parse_metadata_from_manifest(
        cls, manifest_tree: t.Any
    ) -> t.Tuple[t.List[str], t.List[str]]:
        metadata_keys = flatten_manifest_file_keys(manifest_tree)
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

        return (
            serialize_list_of_list_of_strings(build_metadata_keys),
            serialize_list_of_list_of_strings(info_metadata_keys),
        )

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
