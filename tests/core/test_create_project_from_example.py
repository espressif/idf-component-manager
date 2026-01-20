# SPDX-FileCopyrightText: 2024-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import pytest

from idf_component_manager.core import ComponentManager
from idf_component_tools.errors import FatalError
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
