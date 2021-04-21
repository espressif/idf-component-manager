import os
import shutil
import tempfile
from io import open

from idf_component_manager.core import ComponentManager
from idf_component_tools.manifest import MANIFEST_FILENAME, ManifestManager


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
