# SPDX-FileCopyrightText: 2022 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os
import shutil
import tempfile
import warnings

from pytest import raises

from idf_component_manager.context_manager import make_ctx
from idf_component_tools.manifest import MANIFEST_FILENAME, ComponentVersion, SolvedComponent
from idf_component_tools.sources import LocalSource
from idf_component_tools.sources.local import ManifestContextError, SourcePathError


def test_service_is_me():
    assert LocalSource.is_me('test', {'path': '/'})
    assert not LocalSource.is_me('test', {'url': '/'})


def test_download(fixtures_path):
    source = LocalSource(source_details={'path': fixtures_path})
    component = SolvedComponent('cmp', '*', source)
    assert source.download(component, '/test/path/')[0].endswith('fixtures')


def test_versions_without_manifest():
    tempdir = tempfile.mkdtemp()

    try:
        source = LocalSource(source_details={'path': tempdir})
        versions = source.versions('test', spec='*')

        assert versions.name == os.path.basename(tempdir)
        assert versions.versions[0] == ComponentVersion('*')

    finally:
        shutil.rmtree(tempdir)


def test_versions_with_manifest(release_component_path):
    source = LocalSource(source_details={'path': release_component_path})
    versions = source.versions('cmp', spec='*')

    assert versions.name == 'cmp'
    assert versions.versions[0] == ComponentVersion('1.0.0')


def test_local_relative_path_without_context(tmp_path):
    main_component_path = tmp_path / 'project' / 'main'
    os.makedirs(str(main_component_path))
    sub_component_path = tmp_path / 'sub'
    os.makedirs(str(sub_component_path))

    source = LocalSource(source_details={'path': str(os.path.relpath(str(sub_component_path), os.getcwd()))})
    cmp = SolvedComponent('test/cmp', '1.0.1', source)

    with raises(ManifestContextError):
        source.download(cmp, str(main_component_path))


def test_local_relative_path_not_exists(tmp_path):
    main_component_path = tmp_path / 'project' / 'main'
    os.makedirs(str(main_component_path))
    sub_component_path = tmp_path / 'sub'
    os.makedirs(str(sub_component_path))

    with make_ctx('manifest', manifest_path=str(main_component_path / MANIFEST_FILENAME)):
        with raises(SourcePathError):
            source = LocalSource(source_details={'path': '../sub'})
            cmp = SolvedComponent('test/cmp', '1.0.1', source)
            source.download(cmp, str(main_component_path))


def test_local_relative_path_success(tmp_path):
    main_component_path = tmp_path / 'project' / 'main'
    os.makedirs(str(main_component_path))
    sub_component_path = tmp_path / 'sub'
    os.makedirs(str(sub_component_path))

    with make_ctx('manifest', manifest_path=str(main_component_path / MANIFEST_FILENAME)):
        source = LocalSource(source_details={'path': '../../sub'})
        cmp = SolvedComponent('test/cmp', '1.0.1', source)
        assert source.download(cmp, str(main_component_path))
        assert source._path.name == sub_component_path.name  # Path.name for Python <3.6 compatibility


def test_local_path_name_warning(release_component_path):
    warnings.simplefilter('always')
    source = LocalSource(source_details={'path': release_component_path})
    component = SolvedComponent('not_cmp', '*', source)

    with warnings.catch_warnings(record=True) as w:
        source.download(component, 'test')
        assert 'Component name "not_cmp" doesn\'t match the directory name "cmp"' in str(w[-1].message)


def test_local_path_name_no_warning(capsys, release_component_path):
    source = LocalSource(source_details={'path': release_component_path})
    component = SolvedComponent('cmp', '*', source)
    source.download(component, 'test')

    captured = capsys.readouterr()
    assert captured.out == ''
