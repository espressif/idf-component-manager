# SPDX-FileCopyrightText: 2023-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import json

import pytest
import vcr

from idf_component_manager.sync import (
    ComponentStaticVersions,
    collect_metadata,
    dump_metadata,
    get_component_metadata,
    load_saved_metadata,
    metadata_has_changes,
    update_component_metadata,
)
from idf_component_tools.constants import MANIFEST_FILENAME
from idf_component_tools.errors import SyncError
from idf_component_tools.registry.api_models import DependencyResponse
from idf_component_tools.registry.multi_storage_client import MultiStorageClient
from idf_component_tools.registry.service_details import get_storage_client


def test_sync_dependency_with_matches(tmp_path):
    component_path = tmp_path / 'cmp'
    component_path.mkdir()
    (component_path / 'CMakeLists.txt').touch()
    (component_path / MANIFEST_FILENAME).write_text(
        """
    dependencies:
      example/cmp:
        version: "3.3.4"
        matches:
          - if: "idf_version >3.3"
            version: "3.3.3"
          - if: "idf_version <3.3"
            version: "3.3.8"
    """
    )

    metadata = collect_metadata(get_storage_client(), component_path)

    assert ['3.3.3', '3.3.4', '3.3.8'] == sorted([
        v.version for v in metadata['example/cmp'].versions
    ])


def test_sync_dependency_with_rules(tmp_path):
    component_path = tmp_path / 'cmp'
    component_path.mkdir()
    (component_path / 'CMakeLists.txt').touch()
    (component_path / MANIFEST_FILENAME).write_text(
        """
    dependencies:
      example/cmp:
           version: ">3.3.5,<3.3.7"
           rules:
             - if: "idf_version <1.0"
               version: "3.3.8"
             - if: "target in [esp32, esp32c3]"
    """
    )

    metadata = collect_metadata(get_storage_client(), component_path)

    assert ['3.3.6', '3.3.8'] == sorted([v.version for v in metadata['example/cmp'].versions])


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_download_metadata.yaml')
def test_download_metadata_all_versions():
    client = MultiStorageClient(storage_urls=['http://localhost:9000/test-public/'])
    dep = DependencyResponse(source='service', name='test', namespace='espressif', spec='*')
    components, _ = get_component_metadata(client, dep, '*', {}, [])

    assert len(list(components.keys())) == 2
    assert len(components['espressif/test'].versions) == 3
    assert len(components['espressif/cmp'].versions) == 2


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_download_metadata.yaml')
def test_download_metadata_version_with_dependency():
    client = MultiStorageClient(storage_urls=['http://localhost:9000/test-public/'])
    dep = DependencyResponse(source='service', name='test', namespace='espressif', spec='*')
    components, _ = get_component_metadata(client, dep, '==1.0.2', {}, [])

    assert len(components) == 2
    assert len(components['espressif/test'].versions) == 1
    assert len(components['espressif/cmp'].versions) == 2


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_download_metadata.yaml')
def test_download_metadata_version_multiple_versions():
    client = MultiStorageClient(storage_urls=['http://localhost:9000/test-public/'])
    dep = DependencyResponse(source='service', name='test', namespace='espressif', spec='*')
    components, _ = get_component_metadata(client, dep, '<1.0.2', {}, [])

    assert len(components) == 1


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_download_metadata.yaml')
def test_download_metadata_add_metadata():
    client = MultiStorageClient(storage_urls=['http://localhost:9000/test-public/'])
    dep = DependencyResponse(source='service', name='test', namespace='espressif', spec='==1.0.0')
    metadata, _ = get_component_metadata(client, dep, '==1.0.0', {}, [])
    assert len(metadata) == 1
    assert sum([len(data.versions) for data in metadata.values()]) == 1

    metadata, _ = get_component_metadata(client, dep, '==1.0.1', metadata, [])
    assert len(metadata) == 1
    assert sum([len(data.versions) for data in metadata.values()]) == 2


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_download_metadata_unknown_component.yaml')
def test_download_metadata_version_not_found():
    client = MultiStorageClient(storage_urls=['http://localhost:9000/test-public/'])
    dep = DependencyResponse(source='service', name='component', namespace='unknown', spec='*')
    components, warnings = get_component_metadata(client, dep, '*', {}, [])
    assert len(components) == 0

    assert 'Component "unknown/component" with selected spec' in warnings[0]


def test_load_saved_metadata_success(tmp_path):
    path = tmp_path / 'components' / 'example'
    path.mkdir(parents=True)

    with open(str(path / 'cmp.json'), 'w') as f:
        json.dump({'name': 'test', 'versions': []}, f)

    metadata = load_saved_metadata(tmp_path)

    assert 'example/cmp' in metadata
    assert metadata['example/cmp'].metadata == {'name': 'test', 'versions': []}
    assert metadata['example/cmp'].versions == []


def test_load_saved_metadata_file_not_valid(tmp_path):
    path = tmp_path / 'components' / 'example'
    path.mkdir(parents=True)

    with open(str(path / 'cmp.json'), 'w') as f:
        f.write('test')

    with pytest.raises(SyncError):
        load_saved_metadata(tmp_path)


def test_update_component_metadata():
    component_metadata = {
        'name': 'cmp',
        'featured': 'true',
        'versions': [{'version': '0.0.1', 'description': 'test'}],
    }
    api_metadata = {
        'name': 'cmp',
        'featured': 'false',
        'versions': [{'version': '0.0.1', 'description': 'another text'}],
    }

    res = update_component_metadata(component_metadata, api_metadata)

    assert res == {
        'name': 'cmp',
        'featured': 'false',
        'versions': [{'version': '0.0.1', 'description': 'another text'}],
    }

    versions_metadata = {
        'name': 'cmp',
        'featured': 'true',
        'versions': [
            {'version': '0.0.1', 'description': 'another text'},
            {'version': '0.0.2', 'description': 'new version'},
        ],
    }
    res = update_component_metadata(component_metadata, versions_metadata)

    assert res['versions'] == [
        {'version': '0.0.1', 'description': 'another text'},
        {'version': '0.0.2', 'description': 'new version'},
    ]


def test_dump_metadata(tmp_path):
    metadata = {'example/cmp': ComponentStaticVersions({'name': 'cmp', 'versions': []}, [])}

    dump_metadata(metadata, tmp_path)

    with open(str(tmp_path / 'components' / 'example' / 'cmp.json')) as f:
        assert json.load(f) == metadata['example/cmp'].metadata


@pytest.mark.parametrize(
    ('old_metadata', 'new_metadata', 'expected_result'),
    [
        (
            {'name': 'cmp', 'versions': [{'version': '3.3.3'}]},
            {'name': 'cmp', 'versions': [{'version': '3.3.3'}]},
            False,
        ),
        (
            {'name': 'cmp', 'featured': 'true', 'versions': [{'version': '3.3.3'}]},
            {'name': 'cmp', 'featured': 'false', 'versions': [{'version': '3.3.3'}]},
            True,
        ),
        (
            {'name': 'cmp', 'versions': [{'version': '3.3.3'}, {'version': '3.3.4'}]},
            {'name': 'cmp', 'versions': [{'version': '3.3.3'}]},
            False,  # It's ok that versions in old metadata more than in new
        ),
        (
            {'name': 'cmp', 'versions': [{'version': '3.3.3'}]},
            {'name': 'cmp', 'versions': [{'version': '3.3.3'}, {'version': '3.3.4'}]},
            True,  # version should be added
        ),
        (
            {'name': 'cmp', 'versions': [{'version': '3.3.3', 'description': 'test'}]},
            {'name': 'cmp', 'versions': [{'version': '3.3.3', 'description': 'another'}]},
            True,
        ),
        (
            {'name': 'cmp', 'versions': [{'version': '3.3.3'}, {'version': '3.3.4'}]},
            {'name': 'cmp', 'versions': [{'version': '3.3.4'}, {'version': '3.3.3'}]},
            False,
        ),
    ],
)
def test_is_metadata_equal(old_metadata, new_metadata, expected_result):
    result = metadata_has_changes(old_metadata, new_metadata)

    assert expected_result == result
