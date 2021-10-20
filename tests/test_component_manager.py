'''Test Core commands'''
import os
import shutil
import tempfile
from distutils.dir_util import copy_tree
from io import open

import pytest
import vcr

from idf_component_manager.core import ComponentManager
from idf_component_tools.archive_tools import unpack_archive
from idf_component_tools.errors import NothingToDoError
from idf_component_tools.git_client import GitClient
from idf_component_tools.manifest import MANIFEST_FILENAME, ManifestManager

PRE_RELEASE_COMPONENT_PATH = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'fixtures',
    'components',
    'pre',
)

RELEASE_COMPONENT_PATH = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'fixtures',
    'components',
    'cmp',
)


def list_dir(folder):
    res = []
    for root, _, files in os.walk(folder):
        for file in files:
            res.append(os.path.join(root, file))
    return res


def test_init_project():
    tempdir = tempfile.mkdtemp()
    try:
        os.makedirs(os.path.join(tempdir, 'main'))
        os.makedirs(os.path.join(tempdir, 'components', 'foo'))
        main_manifest_path = os.path.join(tempdir, 'main', MANIFEST_FILENAME)
        foo_manifest_path = os.path.join(tempdir, 'components', 'foo', MANIFEST_FILENAME)

        manager = ComponentManager(path=tempdir)
        manager.create_manifest({})
        manager.create_manifest({'component': 'foo'})

        for filepath in [main_manifest_path, foo_manifest_path]:
            with open(filepath, mode='r', encoding='utf-8') as file:
                assert file.readline().startswith('## IDF Component Manager')

        manager.add_dependency({'dependency': 'comp<=1.0.0'})
        manifest_manager = ManifestManager(main_manifest_path, 'main')
        assert manifest_manager.manifest_tree['dependencies']['espressif/comp'] == '<=1.0.0'

        manager.add_dependency({'dependency': 'idf/comp<=1.0.0', 'component': 'foo'})
        manifest_manager = ManifestManager(foo_manifest_path, 'foo')
        assert manifest_manager.manifest_tree['dependencies']['idf/comp'] == '<=1.0.0'
    finally:
        shutil.rmtree(tempdir)


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_upload_component.yaml')
def test_upload_component(monkeypatch):
    monkeypatch.setenv('DEFAULT_COMPONENT_SERVICE_URL', 'http://localhost:5000')
    monkeypatch.setenv('IDF_COMPONENT_API_TOKEN', 'test')
    manager = ComponentManager(path=PRE_RELEASE_COMPONENT_PATH)

    manager.upload_component({
        'name': 'cmp',
        'namespace': 'espressif',
    })


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_check_only_component.yaml')
def test_check_only_upload_component(monkeypatch):
    monkeypatch.setenv('DEFAULT_COMPONENT_SERVICE_URL', 'http://localhost:5000')
    monkeypatch.setenv('IDF_COMPONENT_API_TOKEN', 'test')
    manager = ComponentManager(path=PRE_RELEASE_COMPONENT_PATH)

    manager.upload_component({
        'name': 'cmp',
        'namespace': 'espressif',
        'check_only': True,
    })


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_allow_existing_component.yaml')
def test_allow_existing_component(monkeypatch):
    monkeypatch.setenv('DEFAULT_COMPONENT_SERVICE_URL', 'http://localhost:5000')
    monkeypatch.setenv('IDF_COMPONENT_API_TOKEN', 'test')
    manager = ComponentManager(path=RELEASE_COMPONENT_PATH)

    manager.upload_component({
        'name': 'cmp',
        'namespace': 'espressif',
        'allow_existing': True,
    })


@vcr.use_cassette('tests/fixtures/vcr_cassettes/test_upload_component_skip_pre.yaml')
def test_upload_component_skip_pre(monkeypatch):
    manager = ComponentManager(path=PRE_RELEASE_COMPONENT_PATH)
    monkeypatch.setenv('DEFAULT_COMPONENT_SERVICE_URL', 'http://localhost:5000')
    monkeypatch.setenv('IDF_COMPONENT_API_TOKEN', 'test')

    with pytest.raises(NothingToDoError) as e:
        manager.upload_component({
            'name': 'cmp',
            'namespace': 'espressif',
            'skip_pre_release': True,
        })

    assert str(e.value).startswith('Skipping pre-release')


def test_pack_component(monkeypatch, tmp_path):
    copy_tree(PRE_RELEASE_COMPONENT_PATH, str(tmp_path))
    component_manager = ComponentManager(path=str(tmp_path))

    # remove the first version line
    with open(os.path.join(str(tmp_path), MANIFEST_FILENAME)) as fr:
        lines = fr.readlines()
    with open(os.path.join(str(tmp_path), MANIFEST_FILENAME), 'w') as fw:
        fw.writelines(lines[1:])

    def mock_git_tag(self):
        return '3.0.0'

    monkeypatch.setattr(GitClient, 'get_tag_version', mock_git_tag)

    component_manager.pack_component({
        'name': 'pre',
        'namespace': 'test',
    })

    tempdir = os.path.join(tempfile.tempdir, 'cmp_pre')
    unpack_archive(os.path.join(component_manager.dist_path, 'pre_3.0.0.tgz'), tempdir)
    manifest = ManifestManager(tempdir, 'pre', check_required_fields=True).load()
    assert manifest.version == '3.0.0'
    assert set(list_dir(tempdir)) == set(
        os.path.join(tempdir, file) for file in [
            'idf_component.yml',
            'cmp.c',
            'CMakeLists.txt',
            os.path.join('include', 'cmp.h'),
        ])
