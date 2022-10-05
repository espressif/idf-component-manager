# SPDX-FileCopyrightText: 2022 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os

import pytest

from idf_component_tools.manifest import MANIFEST_FILENAME, ManifestManager


@pytest.fixture(autouse=True)
def mock_token(monkeypatch):
    monkeypatch.setenv('IDF_COMPONENT_API_TOKEN', 'test')


def test_manifest_create_add_dependency(tmp_path, assert_return_code_run):
    tempdir = str(tmp_path)

    os.makedirs(os.path.join(tempdir, 'main'))
    os.makedirs(os.path.join(tempdir, 'components', 'foo'))
    main_manifest_path = os.path.join(tempdir, 'main', MANIFEST_FILENAME)
    foo_manifest_path = os.path.join(tempdir, 'components', 'foo', MANIFEST_FILENAME)

    assert_return_code_run(['compote', 'manifest', 'create'], cwd=tempdir)
    assert_return_code_run(['compote', 'manifest', 'create', '--component', 'foo'], cwd=tempdir)

    for filepath in [main_manifest_path, foo_manifest_path]:
        with open(filepath, mode='r') as file:
            assert file.readline().startswith('## IDF Component Manager')

    assert_return_code_run(['compote', 'manifest', 'add-dependency', 'comp<=1.0.0'], cwd=tempdir)
    manifest_manager = ManifestManager(main_manifest_path, 'main')
    assert manifest_manager.manifest_tree['dependencies']['espressif/comp'] == '<=1.0.0'

    assert_return_code_run(
        ['compote', 'manifest', 'add-dependency', 'idf/comp<=1.0.0', '--component', 'foo'], cwd=tempdir)
    manifest_manager = ManifestManager(foo_manifest_path, 'foo')
    assert manifest_manager.manifest_tree['dependencies']['idf/comp'] == '<=1.0.0'
