# SPDX-FileCopyrightText: 2023-2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import pytest

from idf_component_tools.manifest.metadata import Metadata


def test_metadata(valid_manifest):
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


def test_metadata_treats_overrides_like_dependencies_with_wildcard_keys(valid_manifest):
    valid_manifest['overrides'] = [
        {
            'tinyusb': {
                'with': {
                    'my_tinyusb': {
                        'git': 'https://github.com/micropython/tinyusb-espressif.git',
                        'path': '.',
                        'version': 'cherrypick/dwc2_zlp_fix',
                    }
                }
            }
        }
    ]

    manifest_meta = Metadata.load(valid_manifest)

    assert 'overrides-type:array-*-with-*-git-type:string' in manifest_meta.build_metadata_keys
    assert 'overrides-type:array-*-with-*-path-type:string' in manifest_meta.build_metadata_keys
    assert 'overrides-type:array-*-with-*-version-type:string' in manifest_meta.build_metadata_keys
    assert all(
        not key.startswith('overrides-tinyusb-') for key in manifest_meta.build_metadata_keys
    )


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
