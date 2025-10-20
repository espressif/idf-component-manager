# SPDX-FileCopyrightText: 2022-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import logging
import os
import shutil
import tempfile
import warnings

from pydantic import ValidationError
from pytest import raises

from idf_component_tools import LOGGING_NAMESPACE
from idf_component_tools.manager import ManifestManager
from idf_component_tools.manifest import SolvedComponent
from idf_component_tools.sources import LocalSource
from idf_component_tools.sources.local import ManifestContextError, SourcePathError
from idf_component_tools.utils import ComponentVersion


def sources_if_valid():
    LocalSource(path='/')
    with raises(ValidationError):
        LocalSource(url='/')


def test_download(fixtures_path):
    source = LocalSource(path=fixtures_path)
    component = SolvedComponent(name='cmp', version=ComponentVersion('*'), source=source)
    assert source.download(component, '/test/path/').endswith('fixtures')


def test_versions_without_manifest():
    tempdir = tempfile.mkdtemp()

    try:
        source = LocalSource(path=tempdir)
        versions = source.versions('test', spec='*')

        assert versions.name == os.path.basename(tempdir)
        assert versions.versions[0] == ComponentVersion('*')

    finally:
        shutil.rmtree(tempdir)


def test_versions_with_manifest(release_component_path):
    source = LocalSource(path=release_component_path)
    versions = source.versions('cmp', spec='*')

    assert versions.name == 'cmp'
    assert versions.versions[0] == ComponentVersion('1.0.0')


def test_local_relative_path_without_context(tmp_path):
    main_component_path = tmp_path / 'project' / 'main'
    os.makedirs(str(main_component_path))
    sub_component_path = tmp_path / 'sub'
    os.makedirs(str(sub_component_path))

    source = LocalSource(path=str(os.path.relpath(str(sub_component_path), os.getcwd())))
    cmp = SolvedComponent(name='test/cmp', version=ComponentVersion('1.0.1'), source=source)

    with raises(ManifestContextError):
        source.download(cmp, str(main_component_path))


def test_local_relative_path_not_exists(tmp_path):
    main_component_path = tmp_path / 'project' / 'main'
    os.makedirs(str(main_component_path))
    sub_component_path = tmp_path / 'sub'
    os.makedirs(str(sub_component_path))

    source = LocalSource(
        path='../sub',
        manifest_manager=ManifestManager(main_component_path, 'main'),
    )
    cmp = SolvedComponent(name='test/cmp', version=ComponentVersion('1.0.1'), source=source)

    with raises(SourcePathError):
        source.download(cmp, str(main_component_path))


def test_local_relative_path_success(tmp_path):
    main_component_path = tmp_path / 'project' / 'main'
    os.makedirs(str(main_component_path))
    sub_component_path = tmp_path / 'sub'
    os.makedirs(str(sub_component_path))

    source = LocalSource(
        path='../../sub',
        manifest_manager=ManifestManager(main_component_path, 'main'),
    )
    cmp = SolvedComponent(name='test/cmp', version=ComponentVersion('1.0.1'), source=source)

    assert source.download(cmp, str(main_component_path))
    assert source._path.name == sub_component_path.name  # Path.name for Python <3.6 compatibility


def test_local_path_name_warning(release_component_path, caplog):
    warnings.simplefilter('always')
    source = LocalSource(path=release_component_path)
    component = SolvedComponent(name='not_cmp', version=ComponentVersion('*'), source=source)

    with caplog.at_level(logging.WARNING, logger=LOGGING_NAMESPACE):
        source.download(component, 'test')
        assert len(caplog.records) == 1
        assert 'Component name "not_cmp" doesn\'t match the directory name "cmp"' in str(
            caplog.records[0].message
        )


def test_local_path_name_no_warning(release_component_path, caplog):
    source = LocalSource(path=release_component_path)
    with caplog.at_level(logging.WARNING, logger=LOGGING_NAMESPACE):
        component = SolvedComponent(name='cmp', version=ComponentVersion('*'), source=source)
        source.download(component, 'test')

        assert not caplog.records


def test_local_source_hash_key_equivalence(tmp_path):
    # Setup directory structure
    project = tmp_path / 'project'
    main, com1, com2 = (project / p for p in ['main', 'com/com1', 'com/com2'])
    for d in (main, com1, com2):
        d.mkdir(parents=True)

    # Create dummy manifests and CMakeLists.txt to make them valid components
    (main / 'idf_component.yml').write_text('')
    (com2 / 'idf_component.yml').write_text('')
    (com1 / 'CMakeLists.txt').write_text('')
    (com2 / 'CMakeLists.txt').write_text('')

    # Define local sources with different relative override paths using from_dict
    src_main = LocalSource(
        override_path='../com/com1',
        manifest_manager=ManifestManager(str(main / 'idf_component.yml'), 'main'),
    )
    src_com2 = LocalSource(
        override_path='../com1',
        manifest_manager=ManifestManager(str(com2 / 'idf_component.yml'), 'com2'),
    )
    # They should resolve to the same target and thus have equal hash keys
    assert src_main.hash_key == src_com2.hash_key
