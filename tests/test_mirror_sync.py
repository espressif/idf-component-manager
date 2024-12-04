# SPDX-FileCopyrightText: 2023-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import json
import textwrap

import vcr

from idf_component_manager.core import ComponentManager
from idf_component_manager.sync import (
    collect_component_versions,
    load_local_mirror,
    prepare_component_versions,
    sync_components,
)
from idf_component_manager.utils import VersionSolverResolution
from idf_component_tools import setup_logging
from idf_component_tools.constants import MANIFEST_FILENAME
from idf_component_tools.manifest import ComponentRequirement
from idf_component_tools.registry.multi_storage_client import MultiStorageClient
from idf_component_tools.registry.service_details import get_storage_client
from idf_component_tools.semver import Version


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

    mirror = collect_component_versions(get_storage_client(), component_path)

    assert {
        Version('3.3.3'),
        Version('3.3.4'),
        Version('3.3.8'),
    } == {v.version for v in mirror.data['example/cmp']}


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

    metadata = collect_component_versions(get_storage_client(), component_path)

    assert {
        Version('3.3.6'),
        Version('3.3.8'),
    } == {v.version for v in metadata.data['example/cmp']}


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_download_metadata.yaml')
def test_prepare_component_all_versions():
    client = MultiStorageClient(storage_urls=['http://localhost:9000/test-public/'])
    reqs = [ComponentRequirement(name='espressif/test', version='*')]
    mirror = prepare_component_versions(client, reqs)

    assert len(mirror.data) == 2
    assert len(mirror.data['espressif/test']) == 3
    assert len(mirror.data['espressif/cmp']) == 2


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_download_metadata.yaml')
def test_prepare_component_versions_with_dependency1():
    client = MultiStorageClient(storage_urls=['http://localhost:9000/test-public/'])
    reqs = [ComponentRequirement(name='espressif/test', version='==1.0.2')]
    mirror = prepare_component_versions(client, reqs)

    assert len(mirror.data) == 2
    assert len(mirror.data['espressif/test']) == 1
    assert len(mirror.data['espressif/cmp']) == 2


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_download_metadata.yaml')
def test_prepare_component_versions_with_dependency2():
    client = MultiStorageClient(storage_urls=['http://localhost:9000/test-public/'])
    reqs = [ComponentRequirement(name='espressif/test', version='<1.0.2')]
    mirror = prepare_component_versions(client, reqs)

    assert len(mirror.data) == 1
    assert len(mirror.data['espressif/test']) == 2
    assert 'espressif/cmp' not in mirror.data


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_download_metadata.yaml')
def test_prepare_component_versions_with_multi_dependencies():
    client = MultiStorageClient(storage_urls=['http://localhost:9000/test-public/'])
    reqs = [
        ComponentRequirement(name='espressif/test', version='==1.0.0'),
        ComponentRequirement(name='espressif/test', version='==1.0.1'),
    ]
    mirror = prepare_component_versions(client, reqs)

    assert len(mirror.data) == 1
    assert len(mirror.data['espressif/test']) == 2


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_download_metadata_unknown_component.yaml')
def test_prepare_component_versions_with_unknown_component(caplog):
    client = MultiStorageClient(storage_urls=['http://localhost:9000/test-public/'])
    reqs = [ComponentRequirement(name='unknown/component', version='*')]
    mirror = prepare_component_versions(client, reqs)

    assert mirror.data == {}
    assert (
        'Component "unknown/component" with selected version "*" was not found '
        'in selected storages. Skipping...'
    ) in caplog.text


def test_load_partial_mirror_success(tmp_path, caplog):
    path = tmp_path / 'components' / 'example'
    path.mkdir(parents=True)

    with open(str(path / 'cmp.json'), 'w') as fw:
        json.dump({'name': 'cmp', 'versions': []}, fw)

    mirror = load_local_mirror(tmp_path)

    assert mirror.data == {}
    assert f'Ignoring invalid metadata file: {str(path / "cmp.json")}' not in caplog.text


def test_load_invalid_partial_mirror_file(tmp_path, caplog):
    path = tmp_path / 'components' / 'example'
    path.mkdir(parents=True)

    with open(str(path / 'cmp.json'), 'w') as f:
        f.write('test')

    mirror = load_local_mirror(tmp_path)
    assert mirror.data == {}
    assert f'Ignoring invalid metadata file: {str(path / "cmp.json")}' in caplog.text


# 3.3.8 yanked
# 3.3.9-testcm2 prerelease
def test_update_existing_local_mirror(tmp_path, capsys):
    client = get_storage_client()
    setup_logging()

    # run a range
    sync_components(
        client,
        tmp_path,
        tmp_path,
        components=['example/cmp<3.1'],  # only 3.0.3
    )
    with open(tmp_path / 'components' / 'example' / 'cmp.json') as f:
        data = json.load(f)
    assert len(data['versions']) == 1
    assert sorted([v['version'] for v in data['versions']]) == ['3.0.3']

    assert '1 new files downloaded' in capsys.readouterr().out

    # run a yank version
    sync_components(client, tmp_path, tmp_path, components=['example/cmp==3.3.8'])
    with open(tmp_path / 'components' / 'example' / 'cmp.json') as f:
        data = json.load(f)
    assert len(data['versions']) == 2
    assert sorted([v['version'] for v in data['versions']]) == ['3.0.3', '3.3.8']

    assert '1 new files downloaded' in capsys.readouterr().out

    # run a prerelease version
    sync_components(
        client,
        tmp_path,
        tmp_path,
        components=[
            'example/cmp==3.3.8',  #  duplicate here
            'example/cmp==3.3.9-testcm2',
        ],
    )
    with open(tmp_path / 'components' / 'example' / 'cmp.json') as f:
        data = json.load(f)
    assert len(data['versions']) == 3
    assert sorted([v['version'] for v in data['versions']]) == ['3.0.3', '3.3.8', '3.3.9-testcm2']

    assert '1 new files downloaded' in capsys.readouterr().out


def test_registry_sync_latest_with_two_requirements(tmp_path):
    component_path = tmp_path / 'cmp1'
    component_path.mkdir()
    (component_path / 'main').mkdir()
    with open(component_path / 'main' / 'idf_component.yml', 'w') as fw:
        fw.write(
            textwrap.dedent("""
            dependencies:
              example/cmp: "<3.1"  # latest should be 3.0.3
        """)
        )
    (component_path / 'main' / 'CMakeLists.txt').write_text('\n')

    component_path = tmp_path / 'cmp2'
    component_path.mkdir()
    (component_path / 'main').mkdir()
    with open(component_path / 'main' / 'idf_component.yml', 'w') as fw:
        fw.write(
            textwrap.dedent("""
            dependencies:
              example/cmp: "<3.3.9"  # 3.3.8 is yanked. latest should be 3.3.7
        """)
        )
    (component_path / 'main' / 'CMakeLists.txt').write_text('\n')

    # call
    manager = ComponentManager(path=str(tmp_path))
    manager.sync_registry(
        'default',
        str(tmp_path / 'cache'),
        recursive=True,
        resolution=VersionSolverResolution.LATEST,
    )

    cmp_json = tmp_path / 'cache' / 'components' / 'example' / 'cmp.json'
    with open(cmp_json) as f:
        data = json.load(f)
    assert len(data['versions']) == 2
    assert sorted([v['version'] for v in data['versions']]) == ['3.0.3', '3.3.7']


# this yaml includes
# 3.3.9-testcm2 prerelease
# 3.3.8 yanked
@vcr.use_cassette('tests/fixtures/vcr_cassettes/sync_example_cmp_only_prerelease.yaml')
def test_registry_sync_latest_but_only_got_prerelease(tmp_path, caplog):
    manager = ComponentManager(path=str(tmp_path))
    manager.sync_registry(
        'default',
        str(tmp_path / 'cache'),
        components=['example/cmp'],
        resolution=VersionSolverResolution.LATEST,
    )
    cmp_json = tmp_path / 'cache' / 'components' / 'example' / 'cmp.json'
    with open(cmp_json) as f:
        data = json.load(f)
    assert len(data['versions']) == 1
    assert sorted([v['version'] for v in data['versions']]) == ['3.3.9-testcm2']
    assert 'No stable versions found. Using pre-release versions.' in caplog.text


# this yaml includes
# 3.3.9-testcm2 prerelease
# 3.3.8 yanked
# 3.3.7 stable
@vcr.use_cassette('tests/fixtures/vcr_cassettes/sync_example_cmp.yaml')
def test_registry_sync_latest_but_latest_is_prerelease(tmp_path):
    manager = ComponentManager(path=str(tmp_path))
    manager.sync_registry(
        'default',
        str(tmp_path / 'cache'),
        components=['example/cmp'],
        resolution=VersionSolverResolution.LATEST,
    )
    cmp_json = tmp_path / 'cache' / 'components' / 'example' / 'cmp.json'
    with open(cmp_json) as f:
        data = json.load(f)
    assert len(data['versions']) == 1
    assert sorted([v['version'] for v in data['versions']]) == ['3.3.7']

    # shall only include stable, when stable versions are found
    manager.sync_registry(
        'default',
        str(tmp_path / 'cache2'),
        components=['example/cmp'],
        resolution=VersionSolverResolution.ALL,  #
    )
    cmp_json = tmp_path / 'cache2' / 'components' / 'example' / 'cmp.json'
    with open(cmp_json) as f:
        data = json.load(f)
    assert len(data['versions']) == 1
    assert sorted([v['version'] for v in data['versions']]) == ['3.3.7']

    # shall include prerelease, when use ==
    manager.sync_registry(
        'default',
        str(tmp_path / 'cache3'),
        components=['example/cmp==3.3.9-testcm2'],
        resolution=VersionSolverResolution.ALL,  #
    )
    cmp_json = tmp_path / 'cache3' / 'components' / 'example' / 'cmp.json'
    with open(cmp_json) as f:
        data = json.load(f)
    assert len(data['versions']) == 1
    assert sorted([v['version'] for v in data['versions']]) == ['3.3.9-testcm2']


# this yaml includes
# 3.3.8 yanked
@vcr.use_cassette('tests/fixtures/vcr_cassettes/sync_example_cmp_only_yanked.yaml')
def test_registry_sync_but_only_got_yanked(tmp_path, caplog):
    manager = ComponentManager(path=str(tmp_path))
    manager.sync_registry(
        'default',
        str(tmp_path / 'cache'),
        components=['example/cmp==3.3.8'],
    )
    cmp_json = tmp_path / 'cache' / 'components' / 'example' / 'cmp.json'
    with open(cmp_json) as f:
        data = json.load(f)
    assert len(data['versions']) == 1
    assert sorted([v['version'] for v in data['versions']]) == ['3.3.8']
    assert (
        'The following versions of the "example/cmp" component have been yanked:\n- 3.3.8'
        in caplog.text
    )
