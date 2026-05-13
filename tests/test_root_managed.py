# SPDX-FileCopyrightText: 2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import pytest

from idf_component_tools.errors import FatalError
from idf_component_tools.manifest import Manifest
from idf_component_tools.root_managed_components import (
    RootManagedComponentRecord,
    RootManagedComponentsState,
    RootManagedComponentsStateManager,
    root_managed_component_path,
    validate_root_manifest,
)
from idf_component_tools.root_managed_components.state import FORMAT_VERSION


def _write_component(component_path):
    component_path.mkdir(parents=True, exist_ok=True)
    (component_path / 'CMakeLists.txt').write_text('')
    return component_path


def _record(root_path, name, version, targets=()):
    component_path = _write_component(root_managed_component_path(root_path, name, version))
    return RootManagedComponentRecord(
        name=name,
        version=version,
        path=str(component_path),
        targets=tuple(targets),
    )


def test_root_managed_component_path_is_versioned(tmp_path):
    assert root_managed_component_path(tmp_path, 'espressif/cmp', '1.2.3') == (
        tmp_path / 'espressif' / 'cmp' / '1.2.3' / 'espressif__cmp'
    )


def test_root_managed_component_path_uses_default_namespace(tmp_path):
    assert root_managed_component_path(tmp_path, 'cmp', '1.2.3') == (
        tmp_path / 'espressif' / 'cmp' / '1.2.3' / 'espressif__cmp'
    )


def test_state_round_trip_preserves_records(tmp_path):
    root_path = tmp_path / 'root_managed_components'
    records = [
        _record(root_path, 'example/dep', '1.0.0'),
        _record(root_path, 'example/a', '1.0.0', targets=('esp32', 'esp32s3')),
    ]
    manager = RootManagedComponentsStateManager(root_path / 'root_components.lock')
    manager.dump(RootManagedComponentsState.from_records('hash', records))

    loaded = manager.load()

    assert loaded.manifest_hash == 'hash'
    assert loaded.components['example/a']['1.0.0'].targets == ('esp32', 'esp32s3')
    assert set(loaded.components) == {'example/dep', 'example/a'}


def test_state_load_rejects_invalid_record_version(tmp_path):
    manager = RootManagedComponentsStateManager(tmp_path / 'root_components.lock')
    manager.path.write_text(
        f"version: '{FORMAT_VERSION}'\n"
        'manifest_hash: hash\n'
        'components:\n'
        '  example/cmp:\n'
        '    not-a-version:\n'
        '      path: example/cmp/not-a-version/example__cmp\n',
        encoding='utf-8',
    )

    with pytest.raises(FatalError, match='Invalid root managed component version'):
        manager.load()


def test_validate_root_manifest_allows_registry_dependencies():
    manifest = Manifest.fromdict({'dependencies': {'example/cmp': {'version': '*'}}})

    # Registry (service) sources are the only allowed source; must not raise.
    validate_root_manifest(manifest)


@pytest.mark.parametrize(
    'dependency',
    [
        {'gitcmp': {'git': 'https://example.com/cmp.git'}},
        {'localcmp': {'path': '/tmp/cmp'}},
    ],
)
def test_validate_root_manifest_rejects_non_registry_source(dependency):
    manifest = Manifest.fromdict({'dependencies': dependency})

    with pytest.raises(FatalError, match='ESP Component Registry'):
        validate_root_manifest(manifest)


def test_validate_root_manifest_rejects_conditional_dependencies():
    manifest = Manifest.fromdict({
        'dependencies': {
            'example/cmp': {'rules': [{'if': 'idf_version >= 5.0'}], 'version': '*'},
        }
    })

    with pytest.raises(FatalError, match='conditional dependencies'):
        validate_root_manifest(manifest)
