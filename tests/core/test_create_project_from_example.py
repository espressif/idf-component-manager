# SPDX-FileCopyrightText: 2024-2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import json

import pytest

from idf_component_manager.core import ComponentManager
from idf_component_tools.archive_tools import pack_archive
from idf_component_tools.errors import FatalError, FetchingError
from idf_component_tools.registry.multi_storage_client import MultiStorageClient
from tests.network_test_utils import use_vcr_or_real_env


@use_vcr_or_real_env('tests/fixtures/vcr_cassettes/test_create_example_component_not_exist.yaml')
@pytest.mark.network
def test_create_example_component_not_exist(mock_registry, tmp_path):  # noqa: ARG001
    manager = ComponentManager(path=str(tmp_path))
    with pytest.raises(
        FatalError, match='Component "test_component_manager/non-existent" not found'
    ):
        manager.create_project_from_example('test_component_manager/non-existent:example')


@use_vcr_or_real_env('tests/fixtures/vcr_cassettes/test_create_example_not_exist.yaml')
@pytest.mark.network
def test_create_example_version_not_exist(mock_registry, tmp_path):  # noqa: ARG001
    manager = ComponentManager(path=str(tmp_path))
    with pytest.raises(
        FatalError,
        match='Version of the component "test_component_manager/cmp" satisfying the spec "=2.0.0" was not found.',
    ):
        manager.create_project_from_example('test_component_manager/cmp=2.0.0:example')


@use_vcr_or_real_env('tests/fixtures/vcr_cassettes/test_create_example_not_exist.yaml')
@pytest.mark.network
def test_create_example_not_exist(mock_registry, tmp_path):  # noqa: ARG001
    manager = ComponentManager(path=str(tmp_path))
    with pytest.raises(
        FatalError,
        match='Cannot find example "example" for "test_component_manager/cmp" version "=1.0.0"',
    ):
        manager.create_project_from_example('test_component_manager/cmp=1.0.0:example')


@use_vcr_or_real_env('tests/fixtures/vcr_cassettes/test_create_example_success.yaml')
def test_create_example_success(mock_registry, tmp_path):  # noqa: ARG001
    manager = ComponentManager(path=str(tmp_path))
    manager.create_project_from_example('test_component_manager/cmp>=1.0.0:cmp_ex')


def create_mirror(mirror_path, example_archive=None):
    example_url = 'components/test_component_manager/cmp/1.0.1/examples/cmp_ex.tgz'
    component_json = mirror_path / 'components' / 'test_component_manager' / 'cmp.json'
    component_json.parent.mkdir(parents=True)
    component_json.write_text(
        json.dumps({
            'name': 'cmp',
            'namespace': 'test_component_manager',
            'versions': [
                {
                    'version': '1.0.1',
                    'component_hash': '0' * 64,
                    'url': 'components/test_component_manager/cmp/1.0.1/cmp.zip',
                    'checksums': 'components/test_component_manager/cmp/1.0.1/CHECKSUMS.json',
                    'docs': {},
                    'license': None,
                    'examples': [{'name': 'cmp_ex', 'url': example_url}],
                }
            ],
        })
    )

    if example_archive:
        archive_path = mirror_path / example_url
        archive_path.parent.mkdir(parents=True)
        pack_archive(example_archive, str(archive_path))


def test_create_example_from_local_storage(tmp_path, monkeypatch):
    example_src = tmp_path / 'example_src'
    (example_src / 'main').mkdir(parents=True)
    (example_src / 'main' / 'main.c').write_text('void app_main(void) {}')
    mirror_path = tmp_path / 'mirror'
    create_mirror(mirror_path, example_archive=str(example_src))
    monkeypatch.setenv('IDF_COMPONENT_LOCAL_STORAGE_URL', mirror_path.as_uri())

    project_path = tmp_path / 'project'
    manager = ComponentManager(path=str(tmp_path))
    manager.create_project_from_example(
        'test_component_manager/cmp>=1.0.0:cmp_ex', path=str(project_path)
    )

    assert (project_path / 'main' / 'main.c').read_text() == 'void app_main(void) {}'


@use_vcr_or_real_env('tests/fixtures/vcr_cassettes/test_create_example_success.yaml')
def test_create_example_local_storage_without_archive(
    mock_registry,  # noqa: ARG001
    tmp_path,
    monkeypatch,
    recording_log,
):
    # Mirror created by `compote registry sync` lists examples but has no example archives
    mirror_path = tmp_path / 'mirror'
    create_mirror(mirror_path)
    monkeypatch.setenv('IDF_COMPONENT_LOCAL_STORAGE_URL', mirror_path.as_uri())

    project_path = tmp_path / 'project'
    manager = ComponentManager(path=str(tmp_path))
    manager.create_project_from_example(
        'test_component_manager/cmp>=1.0.0:cmp_ex', path=str(project_path)
    )

    assert any(project_path.iterdir())
    warnings = [r.message for r in recording_log.records if r.level == 'warning']
    assert any('Cannot download example "cmp_ex"' in message for message in warnings)


def test_create_example_reports_all_download_errors(tmp_path, monkeypatch):
    missing_urls = [(tmp_path / name / 'cmp_ex.tgz').as_uri() for name in ('local', 'remote')]
    monkeypatch.setattr(MultiStorageClient, 'example_urls', lambda *_: iter(missing_urls))

    manager = ComponentManager(path=str(tmp_path))
    with pytest.raises(FetchingError) as e:
        manager.create_project_from_example('test_component_manager/cmp>=1.0.0:cmp_ex')

    for url in missing_urls:
        assert url in str(e.value)
