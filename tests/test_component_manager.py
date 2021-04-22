'''Test Core commands'''
import os
import shutil
import tempfile
from io import open

import pytest
import vcr

from idf_component_manager.core import ComponentManager
from idf_component_tools.errors import NothingToDoError
from idf_component_tools.manifest import MANIFEST_FILENAME, ManifestManager

PRE_RELEASE_COMPONENT_PATH = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'fixtures',
    'components',
    'pre',
)


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
