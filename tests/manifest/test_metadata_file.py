# SPDX-FileCopyrightText: 2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import pytest

from idf_component_tools.manifest.metadata import Metadata


def test_metadata(tmp_path, valid_manifest):
    manifest_meta = Metadata.load(valid_manifest)
    assert manifest_meta.build_metadata_keys == [
        'dependencies-*-public-type:boolean',
        'dependencies-*-type:string',
        'dependencies-*-version-type:string',
        'files-exclude-type:array-type:string',
        'files-include-type:array-type:string',
        'targets-type:array-type:string',
        'version-type:string',
    ]
    assert manifest_meta.info_metadata_keys == [
        'description-type:string',
        'discussion-type:string',
        'documentation-type:string',
        'issues-type:string',
        'maintainers-type:array-type:string',
        'repository-type:string',
        'tags-type:array-type:string',
        'url-type:string',
    ]


@pytest.mark.parametrize(
    's, key, types',
    [
        ('files-exclude-type:array-type:string', 'exclude', 'array of string'),
        ('dependencies-*-public-type:boolean', 'public', 'boolean'),
        ('maintainers-type:array-type:string', 'maintainers', 'array of string'),
    ],
)
def test_metadata_get_key_and_types(s, key, types):
    assert key, types == Metadata.get_closest_manifest_key_and_type(s)
