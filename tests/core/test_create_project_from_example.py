# SPDX-FileCopyrightText: 2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import vcr
from pytest import raises

from idf_component_manager.core import ComponentManager
from idf_component_tools.errors import FatalError


def test_create_example_project_path_not_a_directory(tmp_path):
    existing_file = tmp_path / 'example'
    existing_file.write_text('test')

    manager = ComponentManager(path=str(tmp_path))

    with raises(FatalError, match='Your target path is not a directory*'):
        manager.create_project_from_example('test:example')


def test_create_example_project_path_not_empty(tmp_path):
    example_dir = tmp_path / 'example'
    example_dir.mkdir()
    existing_file = example_dir / 'test'
    existing_file.write_text('test')

    manager = ComponentManager(path=str(tmp_path))

    with raises(FatalError, match='To create an example you must*'):
        manager.create_project_from_example('test:example')


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_create_example_component_not_exist.yaml')
def test_create_example_component_not_exist(tmp_path):
    manager = ComponentManager(path=str(tmp_path))
    with raises(FatalError, match='Component "espressif/test" not found'):
        manager.create_project_from_example('test:example')


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_create_example_not_exist.yaml')
def test_create_example_version_not_exist(mock_registry, tmp_path):
    manager = ComponentManager(path=str(tmp_path))
    with raises(
        FatalError,
        match='Version of the component "test/cmp" satisfying the spec "=2.0.0" was not found.',
    ):
        manager.create_project_from_example('test/cmp=2.0.0:example')


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_create_example_not_exist.yaml')
def test_create_example_not_exist(mock_registry, tmp_path):
    manager = ComponentManager(path=str(tmp_path))
    with raises(
        FatalError,
        match='Cannot find example "example" for "test/cmp" version "=1.0.1"',
    ):
        manager.create_project_from_example('test/cmp=1.0.1:example')


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_create_example_success.yaml')
def test_create_example_success(mock_registry, tmp_path):
    manager = ComponentManager(path=str(tmp_path))
    manager.create_project_from_example('test/cmp>=1.0.0:sample_project')
