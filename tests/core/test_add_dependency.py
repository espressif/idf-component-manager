# SPDX-FileCopyrightText: 2022-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
"""Test Core commands"""

import pytest

from idf_component_manager.core import ComponentManager
from idf_component_tools.constants import MANIFEST_FILENAME
from idf_component_tools.errors import FatalError
from idf_component_tools.manager import ManifestManager
from tests.network_test_utils import use_vcr_or_real_env


@use_vcr_or_real_env('tests/fixtures/vcr_cassettes/test_init_project.yaml')
@pytest.mark.network
def test_init_project(mock_registry, tmp_path):
    (tmp_path / 'main').mkdir()
    (tmp_path / 'components' / 'foo').mkdir(parents=True)
    main_manifest_path = tmp_path / 'main' / MANIFEST_FILENAME
    foo_manifest_path = tmp_path / 'components' / 'foo' / MANIFEST_FILENAME

    manager = ComponentManager(path=str(tmp_path))
    manager.create_manifest()
    manager.create_manifest(component='foo')

    for filepath in [main_manifest_path, foo_manifest_path]:
        assert filepath.read_text().startswith('## IDF Component Manager')

    # TODO: Figure out how to test espressif namespace
    # manager.add_dependency('cmp==1.0.0')
    # manifest_manager = ManifestManager(main_manifest_path, 'main')
    # assert manifest_manager.manifest_tree['dependencies']['test/cmp'] == '==1.0.0'

    manager.add_dependency('test_component_manager/cmp==1.0.0', component='foo')
    manifest_manager = ManifestManager(foo_manifest_path, 'foo')
    assert manifest_manager.manifest_tree['dependencies']['test_component_manager/cmp'] == '==1.0.0'


@use_vcr_or_real_env('tests/fixtures/vcr_cassettes/test_init_project_with_path.yaml')
@pytest.mark.network
def test_init_project_with_path(mock_registry, tmp_path):
    src_path = tmp_path / 'src'
    src_path.mkdir(parents=True, exist_ok=True)
    src_manifest_path = src_path / MANIFEST_FILENAME

    outside_project_path = tmp_path.parent
    outside_project_path_error_match = 'Directory ".*" is not under project directory!'
    component_and_path_error_match = 'Cannot determine manifest directory.'

    manager = ComponentManager(path=str(tmp_path))
    manager.create_manifest(path=str(src_path))

    with pytest.raises(FatalError, match=outside_project_path_error_match):
        manager.create_manifest(path=str(outside_project_path))

    with pytest.raises(FatalError, match=component_and_path_error_match):
        manager.create_manifest(component='src', path=str(src_path))

    manager.add_dependency('test_component_manager/cmp==1.0.0', path=str(src_path))
    manifest_manager = ManifestManager(src_manifest_path, 'src')

    assert manifest_manager.manifest_tree['dependencies']['test_component_manager/cmp'] == '==1.0.0'

    with pytest.raises(FatalError, match=outside_project_path_error_match):
        manager.create_manifest(path=str(outside_project_path))

    with pytest.raises(FatalError, match=component_and_path_error_match):
        manager.add_dependency(
            'test_component_manager/cmp==1.0.0', component='src', path=str(src_path)
        )
