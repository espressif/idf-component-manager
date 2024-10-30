# SPDX-FileCopyrightText: 2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import vcr
from pytest import raises

from idf_component_manager.core import ComponentManager
from idf_component_tools.errors import FatalError


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_create_example_component_not_exist.yaml')
def test_create_example_component_not_exist(tmp_path):
    manager = ComponentManager(path=str(tmp_path))
    with raises(FatalError, match='Component "espressif/test" not found'):
        manager.create_project_from_example('test:example')


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_create_example_not_exist.yaml')
def test_create_example_version_not_exist(mock_registry, tmp_path):  # noqa: ARG001
    manager = ComponentManager(path=str(tmp_path))
    with raises(
        FatalError,
        match='Version of the component "test/cmp" satisfying the spec "=2.0.0" was not found.',
    ):
        manager.create_project_from_example('test/cmp=2.0.0:example')


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_create_example_not_exist.yaml')
def test_create_example_not_exist(mock_registry, tmp_path):  # noqa: ARG001
    manager = ComponentManager(path=str(tmp_path))
    with raises(
        FatalError,
        match='Cannot find example "example" for "test/cmp" version "=1.0.1"',
    ):
        manager.create_project_from_example('test/cmp=1.0.1:example')


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_create_example_success.yaml')
def test_create_example_success(mock_registry, tmp_path):  # noqa: ARG001
    manager = ComponentManager(path=str(tmp_path))
    manager.create_project_from_example('test/cmp>=1.0.0:sample_project')
