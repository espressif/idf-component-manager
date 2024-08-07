# SPDX-FileCopyrightText: 2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import vcr
from pytest import raises

from idf_component_manager.core import ComponentManager
from idf_component_tools.errors import FatalError


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_yank_version_success.yaml')
def test_yank_component_version(mock_registry, tmp_path):
    manager = ComponentManager(path=str(tmp_path))
    manager.yank_version('cmp', '1.1.0', 'critical test', namespace='test')


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_yank_version_success.yaml')
def test_yank_component_version_not_exists(mock_registry, tmp_path):
    manager = ComponentManager(path=str(tmp_path))
    with raises(
        FatalError,
        match='Version 1.2.0 of the component "test/cmp" is not on the registry',
    ):
        manager.yank_version('cmp', '1.2.0', 'critical test', namespace='test')
