# SPDX-FileCopyrightText: 2024-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import json
import os
import textwrap
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from idf_component_manager.cmake_component_requirements import (
    CMakeRequirementsManager,
    ComponentName,
)
from idf_component_manager.core import ComponentManager
from idf_component_manager.prepare_components.prepare import _component_list_file
from idf_component_manager.utils import ComponentSource
from idf_component_tools.config import Config, ConfigManager, ProfileItem
from idf_component_tools.constants import IDF_COMPONENT_REGISTRY_URL
from idf_component_tools.errors import FatalError
from idf_component_tools.manifest import Manifest
from idf_component_tools.utils import ProjectRequirements


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
    monkeypatch.setenv('IDF_PATH', str(tmp_path))

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
    monkeypatch.setenv('IDF_PATH', str(tmp_path))

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
    monkeypatch.setenv('IDF_PATH', str(tmp_path))
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
    monkeypatch.setenv('IDF_PATH', str(tmp_path))

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
    monkeypatch.setenv('IDF_PATH', str(tmp_path))

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


def test_overrides_replace_dependency_with_registry_source(tmp_path, monkeypatch):
    monkeypatch.setenv('CI_TESTING_IDF_VERSION', '5.4.0')
    monkeypatch.setenv('IDF_TARGET', 'esp32')
    monkeypatch.setenv('IDF_PATH', str(tmp_path))

    _generate_lock_file(
        tmp_path,
        """
        dependencies:
          example/cmp:
            version: "3.3.9~1"
        overrides:
          - example/cmp:
              with:
                example/cmp:
                  version: "3.3.7"
        """,
    )

    assert (tmp_path / 'dependencies.lock').exists()
    with open(tmp_path / 'dependencies.lock') as f:
        lock_data = YAML(typ='safe').load(f)

    assert lock_data['dependencies']['example/cmp']
    assert lock_data['dependencies']['example/cmp']['source']['type'] == 'service'
    assert lock_data['dependencies']['example/cmp']['version'] == '3.3.7'


def test_overrides_replace_dependency_with_local_source(tmp_path, monkeypatch):
    monkeypatch.setenv('CI_TESTING_IDF_VERSION', '5.4.0')
    monkeypatch.setenv('IDF_TARGET', 'esp32')
    monkeypatch.setenv('IDF_PATH', str(tmp_path))

    local_component_path = tmp_path / 'local_components' / 'example__cmp_override'
    local_component_path.mkdir(parents=True)
    (local_component_path / 'CMakeLists.txt').touch()
    (local_component_path / 'idf_component.yml').write_text(
        textwrap.dedent("""
        version: "2.0.0"
        dependencies:
          idf: ">=5.0"
        """).strip()
    )

    _generate_lock_file(
        tmp_path,
        """
        dependencies:
          example/cmp:
            version: "3.3.9~1"
        overrides:
          - example/cmp:
              with:
                example/cmp-override:
                  path: ../local_components/example__cmp_override
                  version: "*"
        """,
    )

    assert (tmp_path / 'dependencies.lock').exists()
    with open(tmp_path / 'dependencies.lock') as f:
        lock_data = YAML(typ='safe').load(f)

    assert lock_data['dependencies']['example/cmp-override']
    assert lock_data['dependencies']['example/cmp-override']['source']['type'] == 'local'
    assert lock_data['dependencies']['example/cmp-override']['version'] == '2.0.0'


def test_overrides_replace_dependency_with_git_source(tmp_path, monkeypatch):
    monkeypatch.setenv('CI_TESTING_IDF_VERSION', '5.4.0')
    monkeypatch.setenv('IDF_TARGET', 'esp32')
    monkeypatch.setenv('IDF_PATH', str(tmp_path))

    _generate_lock_file(
        tmp_path,
        """
        dependencies:
          example/cmp:
            version: "3.3.9~1"
        overrides:
          - example/cmp:
              with:
                example/cmp-override:
                  git: https://github.com/espressif/example_components.git
                  path: cmp
                  version: 121f1c16ecbf502b8595c869cb3649a5b811b024
        """,
    )

    assert (tmp_path / 'dependencies.lock').exists()
    with open(tmp_path / 'dependencies.lock') as f:
        lock_data = YAML(typ='safe').load(f)

    assert lock_data['dependencies']['example/cmp-override']
    assert lock_data['dependencies']['example/cmp-override']['source']['type'] == 'git'
    assert (
        lock_data['dependencies']['example/cmp-override']['source']['git']
        == 'https://github.com/espressif/example_components.git'
    )
    assert (
        lock_data['dependencies']['example/cmp-override']['version']
        == '121f1c16ecbf502b8595c869cb3649a5b811b024'
    )


def _write_component_requirements_file(path: Path, component_names):
    with open(path, 'w', encoding='utf-8') as f:
        for component_name in component_names:
            for prop in [
                'REQUIRES',
                'PRIV_REQUIRES',
                'MANAGED_REQUIRES',
                'MANAGED_PRIV_REQUIRES',
            ]:
                f.write(f'__component_set_property(___idf_{component_name} {prop} "")\n')
            f.write(
                '__component_set_property(___idf_{component_name} __COMPONENT_SOURCE {source})\n'.format(
                    component_name=component_name,
                    source=ComponentSource.PROJECT_COMPONENTS.value,
                )
            )


def test_inject_requirements_preserves_per_edge_visibility_for_overrides(tmp_path):
    project_dir = tmp_path
    main_dir = project_dir / 'main'
    consumer_dir = project_dir / 'components' / 'consumer'
    main_dir.mkdir(parents=True)
    consumer_dir.mkdir(parents=True)

    (main_dir / 'idf_component.yml').write_text(
        textwrap.dedent("""
        dependencies:
          example/cmp:
            version: '*'
            public: true
        overrides:
          - example/cmp:
              with:
                example/cmp:
                  version: '3.3.7'
        """).strip()
    )
    (consumer_dir / 'idf_component.yml').write_text(
        textwrap.dedent("""
        dependencies:
          example/cmp:
            version: '*'
        """).strip()
    )

    override_requirements = ComponentManager._cmake_override_requirements(
        ProjectRequirements([
            Manifest.fromdict({
                'overrides': [
                    {
                        'example/cmp': {
                            'with': {
                                'example/cmp': {
                                    'version': '3.3.7',
                                }
                            }
                        }
                    }
                ]
            })
        ])
    )
    assert override_requirements == {'example__cmp': {'name': 'example__cmp'}}

    component_list_file = project_dir / 'components_with_manifests.txt'
    component_list_file.write_text(f'{main_dir}\n{consumer_dir}\n')
    with open(ComponentManager._override_requirements_file(component_list_file), 'w') as f:
        json.dump(override_requirements, f)

    component_requires_file = project_dir / 'component_requires.temp.cmake'
    _write_component_requirements_file(component_requires_file, ['main', 'consumer'])

    ComponentManager(str(project_dir), interface_version=3).inject_requirements(
        component_requires_file,
        component_list_file,
        cm_run_counter=0,
    )

    requirements = CMakeRequirementsManager(component_requires_file).load()
    main_requirements = requirements[ComponentName('idf', 'main')]
    consumer_requirements = requirements[ComponentName('idf', 'consumer')]

    assert main_requirements['REQUIRES'] == ['example__cmp']
    assert main_requirements['PRIV_REQUIRES'] == []
    assert consumer_requirements['REQUIRES'] == []
    assert consumer_requirements['PRIV_REQUIRES'] == ['example__cmp']


def test_load_override_requirements_keeps_sidecar_file(tmp_path):
    component_list_file = tmp_path / 'components_with_manifests.txt'
    override_requirements_file = ComponentManager._override_requirements_file(component_list_file)
    with open(override_requirements_file, 'w') as f:
        json.dump({'example__cmp': {'name': 'example__cmp'}}, f)

    override_requirements = ComponentManager(str(tmp_path))._load_override_requirements(
        component_list_file
    )

    assert override_requirements == {'example__cmp': {'name': 'example__cmp'}}
    assert os.path.exists(override_requirements_file)


def test_dependencies_with_constraint_files(tmp_path, monkeypatch):
    """Test dependency resolution with constraint files applied via environment variable."""
    monkeypatch.setenv('CI_TESTING_IDF_VERSION', '5.4.0')
    monkeypatch.setenv('IDF_TARGET', 'esp32')
    monkeypatch.setenv('IDF_PATH', str(tmp_path))

    constraint1 = tmp_path / 'constraints1.txt'
    constraint2 = tmp_path / 'constraints2.txt'
    constraint1.write_text(
        textwrap.dedent("""
        # Primary constraints
        example/cmp==3.3.4
        somethingrandom<1
    """).strip()
    )
    constraint2.write_text(
        textwrap.dedent("""
        # Override constraints (takes precedence)
        example/cmp==3.3.5
    """).strip()
    )

    monkeypatch.setenv('IDF_COMPONENT_CONSTRAINT_FILES', f'{constraint1};{constraint2}')

    _generate_lock_file(
        tmp_path,
        """
        dependencies:
            example/cmp:
                version: '*'
        """,
    )

    assert (tmp_path / 'dependencies.lock').exists()
    with open(tmp_path / 'dependencies.lock') as f:
        lock_data = YAML(typ='safe').load(f)

    resolved_version = lock_data['dependencies']['example/cmp']['version']
    assert resolved_version == '3.3.5'


def test_dependencies_with_constraint_files_and_strings(tmp_path, monkeypatch):
    monkeypatch.setenv('CI_TESTING_IDF_VERSION', '5.4.0')
    monkeypatch.setenv('IDF_TARGET', 'esp32')
    monkeypatch.setenv('IDF_PATH', str(tmp_path))

    # Create a single constraint file
    constraint_file = tmp_path / 'constraints.txt'
    constraint_file.write_text(
        textwrap.dedent("""
        somethingrandom<1
        # Single constraint file
        led_strip==2.5.5
    """).strip()
    )

    # Set single constraint file
    monkeypatch.setenv('IDF_COMPONENT_CONSTRAINT_FILES', str(constraint_file))
    monkeypatch.setenv('IDF_COMPONENT_CONSTRAINTS', 'led_strip<2.5.5')
    _generate_lock_file(
        tmp_path,
        """
        dependencies:
            espressif/led_strip:
                version: '*'
        """,
    )

    assert (tmp_path / 'dependencies.lock').exists()
    with open(tmp_path / 'dependencies.lock') as f:
        lock_data = YAML(typ='safe').load(f)

    # Check that exact version from constraint was used
    assert lock_data['dependencies']['espressif/led_strip']['version'] == '2.5.4'
