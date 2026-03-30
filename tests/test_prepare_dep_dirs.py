# SPDX-FileCopyrightText: 2024-2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest
from ruamel.yaml import YAML

from idf_component_manager.core import ComponentManager
from idf_component_manager.prepare_components.prepare import _component_list_file
from idf_component_tools.config import Config, ConfigManager, ProfileItem
from idf_component_tools.constants import IDF_COMPONENT_REGISTRY_URL
from idf_component_tools.errors import FatalError
from idf_component_tools.registry.api_client import APIClient
from idf_component_tools.registry.client_errors import NetworkConnectionError


def _generate_lock_file(project_dir: Path, yaml_str: str, build_dir: str = 'build'):
    managed_components_list_file = project_dir / build_dir / 'managed_components_list.temp.cmake'
    local_components_list_file = project_dir / build_dir / 'local_components_list.temp.yml'

    os.makedirs(project_dir / 'main', exist_ok=True)
    (project_dir / 'main' / 'CMakeLists.txt').touch()

    (project_dir / 'main' / 'idf_component.yml').write_text(textwrap.dedent(yaml_str))

    os.makedirs(project_dir / build_dir, exist_ok=True)
    ComponentManager(
        path=str(project_dir),
        interface_version=4,
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


def test_dependencies_resolve_with_unreachable_registry_when_local_storage_has_component(
    tmp_path, monkeypatch, caplog
):
    """
    If registry is unreachable but local storage contains required components,
    dependency solving should succeed.

    This test also ensures the "registry storage URL" lookup path was exercised and failed
    (i.e., returned None via NetworkConnectionError), rather than simply never attempting it.
    """

    # Keep environment consistent with existing dep-dir tests
    monkeypatch.setenv('CI_TESTING_IDF_VERSION', '5.4.0')
    monkeypatch.setenv('IDF_TARGET', 'esp32')
    monkeypatch.setenv('IDF_PATH', str(tmp_path))

    cache_dir = tmp_path / 'cache'
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Prepare a local partial mirror that contains the required component version
    ComponentManager('.').sync_registry(
        'default', str(cache_dir), components=['example/cmp==3.0.3']
    )

    # Configure profile with unreachable registry + usable local storage
    ConfigManager().dump(
        Config(
            profiles={
                'tmp_profile': ProfileItem(
                    registry_url='https://my-custom-registry.example.com',
                    storage_url='https://my-custom-registry.example.com',
                    local_storage_url=cache_dir.as_uri(),
                )
            }
        )
    )
    monkeypatch.setenv('IDF_COMPONENT_PROFILE', 'tmp_profile')

    # Force the registry "api_information" call to fail as if the registry is unreachable,
    # and count calls to ensure the code path was actually exercised.
    calls = {'api_information': 0}

    def _api_information_unreachable(*args, **kwargs):
        calls['api_information'] += 1
        raise NetworkConnectionError

    monkeypatch.setattr(APIClient, 'api_information', _api_information_unreachable)

    # Run dependency preparation/solve path and ensure it succeeds
    _generate_lock_file(
        tmp_path,
        """
        dependencies:
          example/cmp:
            version: '*'
        """,
    )

    # We must have attempted to query the registry API for components_base_url at least once,
    # which would have resulted in registry_storage_url returning None internally.
    assert calls['api_information'] >= 1

    # Assert lock file is generated with resolved dependency
    assert (tmp_path / 'dependencies.lock').exists()
    with open(tmp_path / 'dependencies.lock') as f:
        lock_data = YAML(typ='safe').load(f)

    assert lock_data['dependencies']['example/cmp']
    assert lock_data['dependencies']['example/cmp']['version'] == '3.0.3'
    assert lock_data['dependencies']['example/cmp']['source']['type'] == 'service'
    assert (
        lock_data['dependencies']['example/cmp']['source']['registry_url']
        == 'https://my-custom-registry.example.com/'
    )

    # No unreachable-registry warning if resolution succeeded from local storage
    assert (
        'Cannot reach component registry at https://my-custom-registry.example.com'
        not in caplog.text
    )


def test_dependencies_fail_with_unreachable_registry_when_local_storage_lacks_component_version(
    tmp_path, monkeypatch
):
    """
    If registry is unreachable and local storage does not contain the required version,
    dependency solving should fail with a clear fatal error.
    """
    # Keep environment consistent with existing dep-dir tests
    monkeypatch.setenv('CI_TESTING_IDF_VERSION', '5.4.0')
    monkeypatch.setenv('IDF_TARGET', 'esp32')
    monkeypatch.setenv('IDF_PATH', str(tmp_path))

    cache_dir = tmp_path / 'cache'
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Mirror contains only 3.0.3, request 3.3.7 which is not available offline
    ComponentManager('.').sync_registry(
        'default', str(cache_dir), components=['example/cmp==3.0.3']
    )

    # Configure profile with unreachable registry + local storage mirror
    ConfigManager().dump(
        Config(
            profiles={
                'tmp_profile': ProfileItem(
                    registry_url='https://my-custom-registry.example.com',
                    storage_url='https://my-custom-registry.example.com',
                    local_storage_url=cache_dir.as_uri(),
                )
            }
        )
    )
    monkeypatch.setenv('IDF_COMPONENT_PROFILE', 'tmp_profile')

    with pytest.raises(FatalError, match='Are you connected to the internet\\?'):
        _generate_lock_file(
            tmp_path,
            """
            dependencies:
              example/cmp:
                version: '3.3.7'
            """,
        )


def test_root_manifest_with_empty_dependencies_skips_download(tmp_path, monkeypatch):
    """When root idf_extra_components.yml exists but has no dependencies,
    download_project_dependencies should not be called for root components."""
    monkeypatch.setenv('CI_TESTING_IDF_VERSION', '5.4.0')
    monkeypatch.setenv('IDF_TARGET', 'esp32')
    monkeypatch.setenv('IDF_PATH', str(tmp_path))

    # Create root manifest with only comments (no dependencies key) — the real-world default
    tools_dir = tmp_path / 'tools'
    tools_dir.mkdir()
    (tools_dir / 'idf_extra_components.yml').write_text(
        '# This file defines extra dependencies for ESP-IDF\n#dependencies:\n'
    )

    calls = []
    original_download = __import__(
        'idf_component_manager.dependencies', fromlist=['download_project_dependencies']
    ).download_project_dependencies

    def _tracking_download(*args, **kwargs):
        calls.append(args)
        return original_download(*args, **kwargs)

    with patch(
        'idf_component_manager.core.download_project_dependencies',
        side_effect=_tracking_download,
    ):
        _generate_lock_file(
            tmp_path,
            """
            dependencies: {}
            """,
        )

    # No calls should reference root_managed_components paths
    for call_args in calls:
        lock_path = call_args[1]
        assert 'root_managed_components' not in str(lock_path), (
            'download_project_dependencies should not be called for root components '
            'when root manifest has no dependencies'
        )


def test_root_manifest_with_dependencies_triggers_download(tmp_path, monkeypatch):
    """When root idf_extra_components.yml has dependencies,
    download_project_dependencies should be called for them."""
    monkeypatch.setenv('CI_TESTING_IDF_VERSION', '5.4.0')
    monkeypatch.setenv('IDF_TARGET', 'esp32')
    monkeypatch.setenv('IDF_PATH', str(tmp_path))

    # Create root manifest with a dependency
    tools_dir = tmp_path / 'tools'
    tools_dir.mkdir()
    (tools_dir / 'idf_extra_components.yml').write_text(
        textwrap.dedent("""\
        dependencies:
          example/cmp:
            version: '*'
        """)
    )

    calls = []

    def _tracking_download(*args, **kwargs):
        calls.append(args)
        return set()

    with patch(
        'idf_component_manager.core.download_project_dependencies',
        side_effect=_tracking_download,
    ):
        _generate_lock_file(
            tmp_path,
            """
            dependencies: {}
            """,
        )

    root_calls = [c for c in calls if 'root_managed_components' in str(c[1])]
    assert len(root_calls) == 1, (
        'download_project_dependencies should be called once for root components '
        'when root manifest has dependencies'
    )
