# SPDX-FileCopyrightText: 2024-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os
import textwrap
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from idf_component_manager.core import ComponentManager
from idf_component_manager.prepare_components.prepare import _component_list_file
from idf_component_tools.config import Config, ConfigManager, ProfileItem
from idf_component_tools.constants import IDF_COMPONENT_REGISTRY_URL
from idf_component_tools.errors import FatalError


def _generate_lock_file(project_dir: Path, yaml_str: str, build_dir: str = 'build'):
    managed_components_list_file = project_dir / build_dir / 'managed_components_list.temp.cmake'
    local_components_list_file = project_dir / build_dir / 'local_components_list.temp.yml'

    os.makedirs(project_dir / 'main', exist_ok=True)
    (project_dir / 'main' / 'CMakeLists.txt').touch()

    (project_dir / 'main' / 'idf_component.yml').write_text(textwrap.dedent(yaml_str))

    os.makedirs(project_dir / build_dir, exist_ok=True)
    ComponentManager(
        path=str(project_dir),
        interface_version=2,
    ).prepare_dep_dirs(
        managed_components_list_file=str(managed_components_list_file),
        component_list_file=_component_list_file(project_dir / build_dir),
        local_components_list_file=str(local_components_list_file),
    )


def test_dependencies_with_registry_url(tmp_path, monkeypatch):
    monkeypatch.setenv('CI_TESTING_IDF_VERSION', '5.4.0')
    monkeypatch.setenv('IDF_TARGET', 'esp32')
    monkeypatch.setenv('IDF_PATH', '/tmp')

    _generate_lock_file(
        tmp_path,
        """
        dependencies:
            jason-mao/esp_jpeg:  # this one does not exists on production
                version: "*"
                registry_url: "https://components-staging.espressif.com"
        """,
    )

    assert (tmp_path / 'dependencies.lock').exists()
    with open(tmp_path / 'dependencies.lock') as f:
        lock_data = YAML(typ='safe').load(f)

    assert lock_data['dependencies']['jason-mao/esp_jpeg']
    assert (
        lock_data['dependencies']['jason-mao/esp_jpeg']['source']['registry_url']
        == 'https://components-staging.espressif.com'
    )
    assert lock_data['dependencies']['jason-mao/esp_jpeg']['source']['type'] == 'service'


def test_dependencies_with_different_source(tmp_path, monkeypatch):
    monkeypatch.setenv('CI_TESTING_IDF_VERSION', '5.4.0')
    monkeypatch.setenv('IDF_TARGET', 'esp32')
    monkeypatch.setenv('IDF_PATH', '/tmp')

    _generate_lock_file(
        tmp_path,
        """
        dependencies:
          example/cmp:  # this one does not exists on production
            version: "3.3.9~1"
        """,
    )

    assert (tmp_path / 'dependencies.lock').exists()
    with open(tmp_path / 'dependencies.lock') as f:
        lock_data = YAML(typ='safe').load(f)
    assert lock_data['dependencies']['example/cmp']
    assert lock_data['dependencies']['example/cmp']['source']['type'] == 'service'
    touch_timestamp = os.path.getmtime(tmp_path / 'dependencies.lock')
    # use git source instead

    _generate_lock_file(
        tmp_path,
        """
        dependencies:
            example/cmp:  # this one does not exists on production
                version: "121f1c16ecbf502b8595c869cb3649a5b811b024"  # pragma: allowlist secret
                git: "https://github.com/espressif/example_components.git"
                path: "cmp"
        """,
    )

    # modified
    assert os.path.getmtime(tmp_path / 'dependencies.lock') > touch_timestamp

    assert (tmp_path / 'dependencies.lock').exists()
    with open(tmp_path / 'dependencies.lock') as f:
        lock_data = YAML(typ='safe').load(f)
    assert lock_data['dependencies']['example/cmp']
    assert lock_data['dependencies']['example/cmp']['source']['type'] == 'git'


def test_removing_dependency_with_env_var(tmp_path, monkeypatch):
    monkeypatch.setenv('CI_TESTING_IDF_VERSION', '5.4.0')
    monkeypatch.setenv('IDF_TARGET', 'esp32')
    monkeypatch.setenv('IDF_PATH', '/tmp')
    monkeypatch.setenv('BUILD_BOARD', 'esp-box')
    monkeypatch.setenv('IDF_TARGET', 'esp32s3')

    _generate_lock_file(
        tmp_path,
        # Requires BUILD_BOARD env var to be set
        """
        dependencies:
          hfudev/sdl:
            version: '57987dd831bb1f7f022eb364f88886a115d053d8'  # pragma: allowlist secret
            git: https://github.com/hfudev/esp-idf-component-SDL.git
        """,
    )

    # remove this dependency, reconfigure, shall not require env var BUILD_BOARD anymore
    monkeypatch.delenv('BUILD_BOARD')
    _generate_lock_file(
        tmp_path,
        """
        dependencies: {}
        """,
    )


def test_dependencies_with_partial_mirror(tmp_path, monkeypatch):
    monkeypatch.setenv('CI_TESTING_IDF_VERSION', '5.4.0')
    monkeypatch.setenv('IDF_TARGET', 'esp32')
    monkeypatch.setenv('IDF_PATH', '/tmp')

    ComponentManager('.').sync_registry('default', '/tmp/cache', components=['example/cmp==3.0.3'])

    ConfigManager().dump(
        Config(
            profiles={
                'tmp_profile': ProfileItem(
                    registry_url='https://notexist.me',
                    storage_url='https://notexist.me',
                    local_storage_url='file:///tmp/cache',
                )
            }
        )
    )

    monkeypatch.setenv('IDF_COMPONENT_PROFILE', 'tmp_profile')

    _generate_lock_file(
        tmp_path,
        # Requires BUILD_BOARD env var to be set
        """
        dependencies:
          example/cmp:
            version: '*'
        """,
    )

    assert (tmp_path / 'dependencies.lock').exists()
    with open(tmp_path / 'dependencies.lock') as f:
        lock_data = YAML(typ='safe').load(f)
    assert lock_data['dependencies']['example/cmp']
    assert lock_data['dependencies']['example/cmp']['source']['type'] == 'service'
    assert (
        lock_data['dependencies']['example/cmp']['source']['registry_url'] == 'https://notexist.me/'
    )
    assert lock_data['dependencies']['example/cmp']['version'] == '3.0.3'

    # what if depends on a version not in the mirror?
    # registry url still point to a non-existing domain
    with pytest.raises(FatalError, match='Are you connected to the internet?'):
        _generate_lock_file(
            tmp_path,
            # Requires BUILD_BOARD env var to be set
            """
            dependencies:
              example/cmp:
                version: '3.3.7'
            """,
        )

    # back to normal
    ConfigManager().dump(
        Config(
            profiles={
                'tmp_profile': ProfileItem(
                    local_storage_url='file:///tmp/cache',
                )
            }
        )
    )

    _generate_lock_file(
        tmp_path,
        # Requires BUILD_BOARD env var to be set
        """
        dependencies:
            example/cmp:
                version: '3.3.7'
        """,
    )

    assert (tmp_path / 'dependencies.lock').exists()
    with open(tmp_path / 'dependencies.lock') as f:
        lock_data = YAML(typ='safe').load(f)
    assert lock_data['dependencies']['example/cmp']
    assert lock_data['dependencies']['example/cmp']['source']['type'] == 'service'
    assert (
        lock_data['dependencies']['example/cmp']['source']['registry_url']
        == IDF_COMPONENT_REGISTRY_URL
    )
    assert lock_data['dependencies']['example/cmp']['version'] == '3.3.7'


def test_dependencies_case_normalization(tmp_path, monkeypatch):
    monkeypatch.setenv('CI_TESTING_IDF_VERSION', '5.4.0')
    monkeypatch.setenv('IDF_TARGET', 'esp32')
    monkeypatch.setenv('IDF_PATH', '/tmp')

    _generate_lock_file(
        tmp_path,
        """
        dependencies:
            ESP32_Display_Panel:
                version: '*'
            lvgl/lvgl:
                version: ^8
        """,
    )

    assert (tmp_path / 'dependencies.lock').exists()
