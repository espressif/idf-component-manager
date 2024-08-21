# SPDX-FileCopyrightText: 2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os
import textwrap
from pathlib import Path

import yaml

from idf_component_manager.core import ComponentManager
from idf_component_manager.prepare_components.prepare import _component_list_file


def _generate_lock_file(project_dir: Path, yaml_str: str, build_dir: str = 'build'):
    managed_components_list_file = project_dir / build_dir / 'managed_components_list.temp.cmake'
    local_components_list_file = project_dir / build_dir / 'local_components_list.temp.yml'

    os.makedirs(project_dir / 'main')
    (project_dir / 'main' / 'CMakeLists.txt').touch()

    (project_dir / 'main' / 'idf_component.yml').write_text(textwrap.dedent(yaml_str))

    os.makedirs(project_dir / build_dir)

    ComponentManager(
        path=str(project_dir),
        interface_version=2,
    ).prepare_dep_dirs(
        managed_components_list_file=str(managed_components_list_file),
        component_list_file=_component_list_file('build'),
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
            example/cmp:
                version: "*"
                registry_url: "https://components-staging.espressif.com"
        """,
    )

    assert (tmp_path / 'dependencies.lock').exists()
    with open(tmp_path / 'dependencies.lock') as f:
        lock_data = yaml.safe_load(f)

        assert lock_data['dependencies']['example/cmp']
        assert (
            lock_data['dependencies']['example/cmp']['source']['registry_url']
            == 'https://components-staging.espressif.com'
        )
        assert lock_data['dependencies']['example/cmp']['source']['type'] == 'service'
