# SPDX-FileCopyrightText: 2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os
import textwrap
from pathlib import Path

import pytest
import yaml

from idf_component_manager.core import ComponentManager
from idf_component_manager.prepare_components.prepare import _component_list_file
from idf_component_tools.messages import UserNotice


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
        lock_data = yaml.safe_load(f)

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
            hfudev/test_comp:  # this one does not exists on production
                version: "0.4.0"
        """,
    )

    assert (tmp_path / 'dependencies.lock').exists()
    with open(tmp_path / 'dependencies.lock') as f:
        lock_data = yaml.safe_load(f)
    assert lock_data['dependencies']['hfudev/test_comp']
    assert lock_data['dependencies']['hfudev/test_comp']['source']['type'] == 'service'

    # use git source instead
    with pytest.warns(
        UserNotice,
        match='Updating lock file',
    ):
        _generate_lock_file(
            tmp_path,
            """
            dependencies:
                hfudev/test_comp:  # this one does not exists on production
                    version: "f1c676d941c560655117382c914adc49f3fe3935"  # pragma: allowlist secret
                    git: "https://github.com/hfudev/test_proj.git"
        """,
        )

    assert (tmp_path / 'dependencies.lock').exists()
    with open(tmp_path / 'dependencies.lock') as f:
        lock_data = yaml.safe_load(f)
    assert lock_data['dependencies']['hfudev/test_comp']
    assert lock_data['dependencies']['hfudev/test_comp']['source']['type'] == 'git'


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
