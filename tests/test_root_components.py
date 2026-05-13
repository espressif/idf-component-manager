# SPDX-FileCopyrightText: 2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import textwrap
from pathlib import Path

import pytest

from idf_component_manager.root_components.install import (
    _best_versions_per_target,
    _download_requirement_versions,
    install_root_components,
)
from idf_component_tools.config import root_managed_components_dir
from idf_component_tools.errors import FatalError
from idf_component_tools.manager import ManifestManager
from idf_component_tools.manifest import Manifest
from idf_component_tools.root_managed_components import (
    RootManagedComponentsStateManager,
    root_managed_component_path,
    root_managed_components_state_path,
)
from idf_component_tools.utils import HashedComponentVersion
from tests.network_test_utils import use_vcr_or_real_env


@pytest.fixture
def idf_env(tmp_path, monkeypatch):
    """Set up a minimal ESP-IDF-like environment with IDF_PATH and IDF_TOOLS_PATH."""
    idf_dir = tmp_path / 'esp-idf'
    idf_dir.mkdir()
    (idf_dir / 'tools').mkdir()

    tools_dir = tmp_path / 'tools_dir'
    tools_dir.mkdir()

    monkeypatch.setenv('CI_TESTING_IDF_VERSION', '5.4.0')
    monkeypatch.setenv('IDF_PATH', str(idf_dir))
    monkeypatch.setenv('IDF_TOOLS_PATH', str(tools_dir))

    return idf_dir, tools_dir


def test_install_no_manifest(idf_env):  # noqa: ARG001
    """Should be a no-op (no error) when idf_extra_components.yml doesn't exist."""
    install_root_components()
    # No error — nothing to clean up


def test_install_no_manifest_cleans_root_components(idf_env):  # noqa: ARG001
    """Missing idf_extra_components.yml should remove stale root managed components."""
    root_dir = root_managed_components_dir()
    root_dir.mkdir(parents=True)
    (root_dir / 'stale').write_text('stale')

    install_root_components()

    assert not root_dir.exists()


def test_install_empty_dependencies_cleans_root_components(idf_env):
    """Should remove existing root managed components when manifest has no dependencies."""
    idf_dir, _ = idf_env
    root_dir = root_managed_components_dir()
    root_dir.mkdir(parents=True)
    (root_dir / 'stale').write_text('stale')
    (idf_dir / 'tools' / 'idf_extra_components.yml').write_text('# No dependencies\n')

    install_root_components()

    assert not root_dir.exists()


def test_best_versions_per_target_selects_target_specific_fallbacks():
    selected = _best_versions_per_target([
        HashedComponentVersion('1.4.0', component_hash='h4', targets=['esp32s3']),
        HashedComponentVersion('1.3.0', component_hash='h3', targets=['esp32', 'esp32s3']),
    ])

    assert {str(version.version) for version in selected} == {'1.3.0', '1.4.0'}


def test_best_versions_per_target_prefers_newer_universal_version():
    selected = _best_versions_per_target([
        HashedComponentVersion('1.4.0', component_hash='h4'),
        HashedComponentVersion('1.3.0', component_hash='h3', targets=['esp32']),
    ])

    assert [str(version.version) for version in selected] == ['1.4.0']


@use_vcr_or_real_env('tests/fixtures/vcr_cassettes/test_root_download_requirement_versions.yaml')
@pytest.mark.network
def test_download_requirement_versions_downloads_to_root_layout(
    idf_env,
    mock_registry,  # noqa: ARG001
    monkeypatch,
):
    _, tools_dir = idf_env
    monkeypatch.setenv('IDF_COMPONENT_CACHE_PATH', str(tools_dir / 'cache'))
    manifest = Manifest.fromdict({
        'dependencies': {'test_component_manager/cmp': {'version': '=1.0.1'}}
    })

    downloaded = _download_requirement_versions(
        manifest.raw_requirements[0], str(root_managed_components_dir()), set()
    )

    assert len(downloaded) == 1
    component = downloaded[0]
    expected_path = root_managed_component_path(
        root_managed_components_dir(), 'test_component_manager/cmp', '1.0.1'
    )
    assert Path(component.abs_path).resolve() == expected_path.resolve()
    assert component.component_name == 'test_component_manager/cmp'
    assert component.version == '1.0.1'
    assert (expected_path / 'idf_component.yml').is_file()


@use_vcr_or_real_env('tests/fixtures/vcr_cassettes/test_root_components_install.yaml')
@pytest.mark.network
def test_install_downloads_and_serializes_component_as_record(idf_env, mock_registry, monkeypatch):  # noqa: ARG001
    idf_dir, tools_dir = idf_env
    monkeypatch.setenv('IDF_COMPONENT_CACHE_PATH', str(tools_dir / 'cache'))
    manifest_path = idf_dir / 'tools' / 'idf_extra_components.yml'
    manifest_path.write_text(
        textwrap.dedent("""\
        dependencies:
          test_component_manager/stb_and_ynk_and_pre:
            version: '=1.0.1'
        """)
    )

    install_root_components()

    state = RootManagedComponentsStateManager(root_managed_components_state_path()).load()
    record = state.components['test_component_manager/stb_and_ynk_and_pre']['1.0.1']
    expected_path = root_managed_component_path(
        root_managed_components_dir(), 'test_component_manager/stb_and_ynk_and_pre', '1.0.1'
    )
    assert Path(record.path).resolve() == expected_path.resolve()
    assert record.targets == ()
    assert not hasattr(record, 'requirements')
    assert state.manifest_hash == ManifestManager(str(manifest_path), 'root').load().manifest_hash


def test_install_rejects_conditional_root_dependencies(idf_env):
    idf_dir, _ = idf_env
    (idf_dir / 'tools' / 'idf_extra_components.yml').write_text(
        textwrap.dedent("""\
        dependencies:
          example/cmp:
            version: '*'
            rules:
              - if: target == esp32
        """)
    )

    with pytest.raises(FatalError, match='uses "rules"'):
        install_root_components()
